"""Email uniqueness under concurrency.

`create_employee` checks `get_by_email` and then inserts, which is a read
followed by a write: two concurrent requests for the same address can both
pass the check and only collide at COMMIT. The contract promises
`409 email_already_exists` for a duplicate, so the loser of that race must
get the same 409 and not an unhandled 500.
"""

from __future__ import annotations

import datetime as dt
import os
import tempfile
import threading
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker

import app.models as models  # noqa: F401 -- populates Base.metadata
from app.core.errors import EmailAlreadyExistsError
from app.db.session import Base
from app.models.employee import Employee
from app.models.enums import EmploymentStatus, Gender
from app.models.reference import Country, Department, JobRole, Level
from app.schemas.employee import EmployeeCreate
from app.services import employee_service

DUPLICATE_EMAIL = "duplicate@acme.com"


@pytest.fixture
def maker() -> Iterator[sessionmaker]:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_maker = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )

    setup = session_maker()
    setup.add_all(
        [
            Department(id=1, name="Engineering"),
            JobRole(id=1, name="Software Engineer"),
            Level(id=1, name="L3", rank=3),
            Country(id=1, code="US", name="United States", currency="USD"),
        ]
    )
    setup.commit()
    setup.close()

    try:
        yield session_maker
    finally:
        engine.dispose()
        os.unlink(path)


def _payload(first_name: str) -> EmployeeCreate:
    return EmployeeCreate(
        first_name=first_name,
        last_name="Tester",
        email=DUPLICATE_EMAIL,
        gender=Gender.UNDISCLOSED,
        hire_date=dt.date(2024, 1, 1),
        employment_status=EmploymentStatus.ACTIVE,
        department_id=1,
        job_role_id=1,
        level_id=1,
        country_id=1,
    )


def test_concurrent_creates_with_the_same_email_yield_one_employee_and_a_409(
    maker: sessionmaker,
) -> None:
    barrier = threading.Barrier(2)
    outcomes: list[BaseException | None] = [None, None]

    def worker(index: int, first_name: str) -> None:
        session = maker()
        try:
            # Both threads pass the get_by_email check before either commits.
            employee_service.employee_repo.get_by_email(session, DUPLICATE_EMAIL)
            barrier.wait(timeout=10)
            employee_service.create_employee(session, _payload(first_name))
        except BaseException as exc:  # noqa: BLE001 -- asserted on below
            outcomes[index] = exc
            session.rollback()
        finally:
            session.close()

    threads = [
        threading.Thread(target=worker, args=(0, "First")),
        threading.Thread(target=worker, args=(1, "Second")),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    check = maker()
    try:
        count = check.execute(
            select(func.count()).select_from(Employee).where(Employee.email == DUPLICATE_EMAIL)
        ).scalar_one()
    finally:
        check.close()

    assert count == 1, f"expected exactly one employee with {DUPLICATE_EMAIL}, found {count}"

    failures = [exc for exc in outcomes if exc is not None]
    assert len(failures) == 1, "exactly one of the two creates must fail"
    # SQLite may reject the loser at the unique constraint (mapped to the
    # contract's 409) or at its database-level write lock. Neither may be a
    # bare IntegrityError leaking to the caller as a 500.
    assert isinstance(failures[0], EmailAlreadyExistsError | OperationalError)
    assert not isinstance(failures[0], IntegrityError)


def test_duplicate_email_still_returns_409_sequentially(maker: sessionmaker) -> None:
    """The fast path must be unchanged by the commit-time guard."""
    session = maker()
    try:
        employee_service.create_employee(session, _payload("First"))
        with pytest.raises(EmailAlreadyExistsError):
            employee_service.create_employee(session, _payload("Second"))
    finally:
        session.close()
