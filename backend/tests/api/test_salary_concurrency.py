"""The append-only invariant under concurrency.

`docs/decisions/ADR-002` claims an employee can never have two "current"
salaries. Sequential tests in `test_salary.py` cover the happy path, but the
interesting failure is two raises racing each other: both transactions read
the same open record before either commits, both close it, and both insert a
new open row.

These tests force exactly that interleaving with a `threading.Barrier` (no
sleeps, so they are deterministic rather than timing-dependent) and assert
that the database refuses the second open record. The guarantee comes from
the partial unique index on `salary_records` -- SQLite has no row-level
locking, so `SELECT ... FOR UPDATE` is a no-op here and the index is what
actually holds the line. On Postgres both mechanisms apply.
"""

from __future__ import annotations

import datetime as dt
import os
import tempfile
import threading
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker

import app.models as models  # noqa: F401 -- populates Base.metadata
from app.core.errors import ConcurrentSalaryChangeError
from app.db.session import Base
from app.models.employee import Employee
from app.models.enums import ChangeReason, EmploymentStatus, Gender
from app.models.reference import Country, Department, JobRole, Level
from app.models.salary_record import SalaryRecord
from app.services import salary_service


@pytest.fixture
def concurrent_env() -> Iterator[tuple[sessionmaker, int]]:
    """A temp-file SQLite DB (shared across threads) holding one employee with
    one open salary record."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    setup = maker()
    setup.add_all(
        [
            Department(id=1, name="Engineering"),
            JobRole(id=1, name="Software Engineer"),
            Level(id=1, name="L3", rank=3),
            Country(id=1, code="US", name="United States", currency="USD"),
        ]
    )
    setup.flush()
    setup.add(
        Employee(
            id=1,
            employee_code="ACME-000001",
            first_name="Ada",
            last_name="Lovelace",
            email="ada@acme.com",
            gender=Gender.FEMALE,
            hire_date=dt.date(2020, 1, 1),
            employment_status=EmploymentStatus.ACTIVE,
            department_id=1,
            job_role_id=1,
            level_id=1,
            country_id=1,
        )
    )
    setup.flush()
    setup.add(
        SalaryRecord(
            employee_id=1,
            amount_minor=10_000_000,
            currency="USD",
            effective_from=dt.date(2020, 1, 1),
            effective_to=None,
            change_reason=ChangeReason.INITIAL,
        )
    )
    setup.commit()
    setup.close()

    try:
        yield maker, 1
    finally:
        engine.dispose()
        os.unlink(path)


def _race(maker: sessionmaker, employee_id: int, amounts: list[str]) -> list[BaseException | None]:
    """Run one `record_salary_change` per amount, each in its own session, with
    every thread forced to read the current record before any of them commits."""
    barrier = threading.Barrier(len(amounts))
    outcomes: list[BaseException | None] = [None] * len(amounts)

    def worker(index: int, amount: str) -> None:
        session = maker()
        try:
            # Everyone reads the same "current" record first...
            salary_service.salary_repo.get_open_record(session, employee_id)
            barrier.wait(timeout=10)
            # ...then they all try to replace it.
            salary_service.record_salary_change(
                session,
                employee_id=employee_id,
                amount=amount,
                currency="USD",
                effective_from=dt.date(2024, 1, 1),
                change_reason=ChangeReason.ANNUAL_REVIEW,
                note=None,
            )
            session.commit()
        except BaseException as exc:  # noqa: BLE001 -- recorded and asserted on below
            outcomes[index] = exc
            session.rollback()
        finally:
            session.close()

    threads = [threading.Thread(target=worker, args=(i, amt)) for i, amt in enumerate(amounts)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    return outcomes


def _open_records(maker: sessionmaker, employee_id: int) -> list[SalaryRecord]:
    session = maker()
    try:
        return list(
            session.execute(
                select(SalaryRecord).where(
                    SalaryRecord.employee_id == employee_id,
                    SalaryRecord.effective_to.is_(None),
                )
            )
            .scalars()
            .all()
        )
    finally:
        session.close()


def test_concurrent_raises_leave_exactly_one_open_record(
    concurrent_env: tuple[sessionmaker, int],
) -> None:
    maker, employee_id = concurrent_env

    _race(maker, employee_id, ["120000.00", "110000.00"])

    open_records = _open_records(maker, employee_id)
    assert len(open_records) == 1, (
        f"expected exactly one open salary record, found {len(open_records)}: "
        f"{[(r.id, r.amount_minor) for r in open_records]}"
    )


def test_losing_concurrent_raise_is_a_conflict_not_a_crash(
    concurrent_env: tuple[sessionmaker, int],
) -> None:
    """The loser must fail as a retryable conflict, never as an unhandled error."""
    maker, employee_id = concurrent_env

    outcomes = _race(maker, employee_id, ["120000.00", "110000.00"])

    failures = [exc for exc in outcomes if exc is not None]
    assert len(failures) <= 1, "at most one of the two raises may fail"
    for exc in failures:
        # SQLite may reject the loser at either layer: the partial unique
        # index (mapped to ConcurrentSalaryChangeError) or its database-level
        # write lock. Both are conflicts; neither is a crash.
        assert isinstance(exc, ConcurrentSalaryChangeError | OperationalError), (
            f"loser failed with {type(exc).__name__}: {exc}"
        )
        if isinstance(exc, OperationalError):
            assert "locked" in str(exc).lower()


def test_history_stays_gapless_after_a_concurrent_raise(
    concurrent_env: tuple[sessionmaker, int],
) -> None:
    """The winner's timeline must still be contiguous: the loser's rolled-back
    close must not leave a stale `effective_to` behind."""
    maker, employee_id = concurrent_env

    _race(maker, employee_id, ["120000.00", "110000.00"])

    session = maker()
    try:
        records = list(
            session.execute(
                select(SalaryRecord)
                .where(SalaryRecord.employee_id == employee_id)
                .order_by(SalaryRecord.effective_from)
            )
            .scalars()
            .all()
        )
    finally:
        session.close()

    for earlier, later in zip(records, records[1:], strict=False):
        assert earlier.effective_to is not None, "a superseded record must be closed"
        assert earlier.effective_to == later.effective_from - dt.timedelta(days=1), (
            "closed record must end exactly one day before the next one starts"
        )
    assert records[-1].effective_to is None


def test_partial_unique_index_rejects_a_second_open_record(
    concurrent_env: tuple[sessionmaker, int],
) -> None:
    """The guarantee is structural, not just a convention in the service layer:
    inserting a second open record directly must be refused by the database."""
    maker, employee_id = concurrent_env

    session = maker()
    try:
        session.add(
            SalaryRecord(
                employee_id=employee_id,
                amount_minor=99_000_000,
                currency="USD",
                effective_from=dt.date(2025, 1, 1),
                effective_to=None,
                change_reason=ChangeReason.CORRECTION,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
    finally:
        session.rollback()
        session.close()

    assert len(_open_records(maker, employee_id)) == 1


def test_closed_records_are_not_constrained(
    concurrent_env: tuple[sessionmaker, int],
) -> None:
    """The index must only constrain OPEN records -- an employee can have any
    number of closed historical records."""
    maker, employee_id = concurrent_env

    session = maker()
    try:
        session.add_all(
            [
                SalaryRecord(
                    employee_id=employee_id,
                    amount_minor=1_000_000 * n,
                    currency="USD",
                    effective_from=dt.date(2015 + n, 1, 1),
                    effective_to=dt.date(2015 + n, 12, 31),
                    change_reason=ChangeReason.ANNUAL_REVIEW,
                )
                for n in range(1, 4)
            ]
        )
        session.commit()
    finally:
        session.close()

    assert len(_open_records(maker, employee_id)) == 1
