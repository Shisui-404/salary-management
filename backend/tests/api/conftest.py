"""API test fixtures: a fresh temp-file SQLite database per test, wired into
the FastAPI app via a `get_db` dependency override, plus a small hand-built
~12-employee "fixture org" whose expected numbers are computed by hand in
the tests themselves (see the module docstring on `test_analytics.py`).

Every test gets its own temp `.db` file (not `:memory:`) so behaviour matches
the real SQLite file the app runs against, and no test can see another
test's data — full isolation, no shared state, no ordering dependence.
"""

from __future__ import annotations

import datetime as dt
import os
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models as models  # noqa: F401 -- populates Base.metadata
from app.db.session import Base, get_db
from app.main import app
from app.models.currency_rate import CurrencyRate
from app.models.employee import Employee
from app.models.enums import ChangeReason, EmploymentStatus, Gender
from app.models.reference import Country, Department, JobRole, Level
from app.models.salary_band import SalaryBand
from app.models.salary_record import SalaryRecord


@pytest.fixture
def db_session() -> Iterator[Session]:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        os.unlink(path)


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    def _override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@dataclass(frozen=True)
class FixtureIds:
    department_engineering: int
    department_sales: int
    role_swe: int
    role_sales_rep: int
    level_l1: int
    level_l2: int
    level_l3: int
    country_us: int
    country_in: int
    # employee ids, in creation order (Alice .. Leo)
    alice: int
    bob: int
    carol: int
    dave: int
    eve: int
    frank: int
    grace: int
    henry: int
    ivy: int
    jack: int
    karen: int
    leo: int


def _make_employee(
    db: Session,
    *,
    first: str,
    last: str,
    gender: Gender,
    status: EmploymentStatus,
    dept_id: int,
    role_id: int,
    level_id: int,
    country_id: int,
    hire_date: dt.date,
    salary_amount: str,
    salary_currency: str,
) -> Employee:
    emp = Employee(
        employee_code="",
        first_name=first,
        last_name=last,
        email=f"{first.lower()}.{last.lower()}@acme.com",
        gender=gender,
        hire_date=hire_date,
        employment_status=status,
        department_id=dept_id,
        job_role_id=role_id,
        level_id=level_id,
        country_id=country_id,
    )
    db.add(emp)
    db.flush()
    emp.employee_code = f"ACME-{emp.id:06d}"
    db.add(
        SalaryRecord(
            employee_id=emp.id,
            amount_minor=int(Decimal(salary_amount) * 100),
            currency=salary_currency,
            effective_from=hire_date,
            effective_to=None,
            change_reason=ChangeReason.INITIAL,
            note=None,
        )
    )
    return emp


@pytest.fixture
def fixture_org(db_session: Session) -> FixtureIds:
    """Seeds the ~12-employee hand-built org used throughout `tests/api/`.

    Every expected statistic used in the analytics tests is derived from
    *exactly* this data — see the worked-by-hand numbers documented at the
    top of `test_analytics.py`. Changing any salary/department/role/level/
    country value here without updating those numbers will break those
    tests; that coupling is deliberate (it is what makes "exact computed
    value" assertions possible at all).
    """
    db = db_session

    engineering = Department(name="Engineering")
    sales = Department(name="Sales")
    db.add_all([engineering, sales])

    swe = JobRole(name="Software Engineer")
    sales_rep = JobRole(name="Sales Representative")
    db.add_all([swe, sales_rep])

    l1 = Level(name="L1", rank=1)
    l2 = Level(name="L2", rank=2)
    l3 = Level(name="L3", rank=3)
    db.add_all([l1, l2, l3])

    us = Country(name="United States", code="US", currency="USD")
    india = Country(name="India", code="IN", currency="INR")
    db.add_all([us, india])
    db.flush()

    db.add_all(
        [
            CurrencyRate(
                currency="USD", rate_to_base=Decimal("1.00"), valid_from=dt.date(2024, 1, 1)
            ),
            CurrencyRate(
                currency="INR", rate_to_base=Decimal("0.01"), valid_from=dt.date(2024, 1, 1)
            ),
        ]
    )

    db.add_all(
        [
            SalaryBand(
                job_role_id=swe.id,
                level_id=l1.id,
                country_id=us.id,
                min_minor=6_000_000,
                mid_minor=7_000_000,
                max_minor=8_500_000,
                currency="USD",
            ),
            SalaryBand(
                job_role_id=swe.id,
                level_id=l2.id,
                country_id=us.id,
                min_minor=8_500_000,
                mid_minor=10_000_000,
                max_minor=12_000_000,
                currency="USD",
            ),
            SalaryBand(
                job_role_id=swe.id,
                level_id=l3.id,
                country_id=us.id,
                min_minor=11_000_000,
                mid_minor=12_500_000,
                max_minor=14_500_000,
                currency="USD",
            ),
            SalaryBand(
                job_role_id=swe.id,
                level_id=l2.id,
                country_id=india.id,
                min_minor=600_000,
                mid_minor=750_000,
                max_minor=900_000,
                currency="USD",
            ),
            SalaryBand(
                job_role_id=sales_rep.id,
                level_id=l1.id,
                country_id=us.id,
                min_minor=4_500_000,
                mid_minor=5_200_000,
                max_minor=6_000_000,
                currency="USD",
            ),
            # Deliberately no band for (Sales Representative, L3, US) -- Jack
            # Jones is the fixture's "unbanded" employee.
        ]
    )
    db.flush()

    d = dt.date
    alice = _make_employee(
        db,
        first="Alice",
        last="Anderson",
        gender=Gender.FEMALE,
        status=EmploymentStatus.ACTIVE,
        dept_id=engineering.id,
        role_id=swe.id,
        level_id=l2.id,
        country_id=us.id,
        hire_date=d(2019, 1, 10),
        salary_amount="100000.00",
        salary_currency="USD",
    )
    bob = _make_employee(
        db,
        first="Bob",
        last="Baker",
        gender=Gender.MALE,
        status=EmploymentStatus.ACTIVE,
        dept_id=engineering.id,
        role_id=swe.id,
        level_id=l2.id,
        country_id=us.id,
        hire_date=d(2019, 6, 1),
        salary_amount="110000.00",
        salary_currency="USD",
    )
    carol = _make_employee(
        db,
        first="Carol",
        last="Chen",
        gender=Gender.FEMALE,
        status=EmploymentStatus.ACTIVE,
        dept_id=engineering.id,
        role_id=swe.id,
        level_id=l2.id,
        country_id=us.id,
        hire_date=d(2020, 1, 1),
        salary_amount="90000.00",
        salary_currency="USD",
    )
    dave = _make_employee(
        db,
        first="Dave",
        last="Diaz",
        gender=Gender.MALE,
        status=EmploymentStatus.ACTIVE,
        dept_id=engineering.id,
        role_id=swe.id,
        level_id=l2.id,
        country_id=us.id,
        hire_date=d(2020, 6, 1),
        salary_amount="115000.00",
        salary_currency="USD",
    )
    eve = _make_employee(
        db,
        first="Eve",
        last="Evans",
        gender=Gender.FEMALE,
        status=EmploymentStatus.ACTIVE,
        dept_id=engineering.id,
        role_id=swe.id,
        level_id=l2.id,
        country_id=india.id,
        hire_date=d(2021, 1, 1),
        salary_amount="700000.00",
        salary_currency="INR",
    )
    frank = _make_employee(
        db,
        first="Frank",
        last="Fox",
        gender=Gender.MALE,
        status=EmploymentStatus.ACTIVE,
        dept_id=engineering.id,
        role_id=swe.id,
        level_id=l2.id,
        country_id=india.id,
        hire_date=d(2021, 6, 1),
        salary_amount="750000.00",
        salary_currency="INR",
    )
    grace = _make_employee(
        db,
        first="Grace",
        last="Green",
        gender=Gender.FEMALE,
        status=EmploymentStatus.ACTIVE,
        dept_id=engineering.id,
        role_id=swe.id,
        level_id=l1.id,
        country_id=us.id,
        hire_date=d(2022, 1, 1),
        salary_amount="70000.00",
        salary_currency="USD",
    )
    henry = _make_employee(
        db,
        first="Henry",
        last="Hall",
        gender=Gender.MALE,
        status=EmploymentStatus.ACTIVE,
        dept_id=engineering.id,
        role_id=swe.id,
        level_id=l1.id,
        country_id=us.id,
        hire_date=d(2022, 6, 1),
        salary_amount="75000.00",
        salary_currency="USD",
    )
    ivy = _make_employee(
        db,
        first="Ivy",
        last="Ito",
        gender=Gender.FEMALE,
        status=EmploymentStatus.ON_LEAVE,
        dept_id=engineering.id,
        role_id=swe.id,
        level_id=l3.id,
        country_id=us.id,
        hire_date=d(2018, 1, 1),
        salary_amount="150000.00",
        salary_currency="USD",
    )
    jack = _make_employee(
        db,
        first="Jack",
        last="Jones",
        gender=Gender.MALE,
        status=EmploymentStatus.ACTIVE,
        dept_id=sales.id,
        role_id=sales_rep.id,
        level_id=l3.id,
        country_id=us.id,
        hire_date=d(2023, 1, 1),
        salary_amount="90000.00",
        salary_currency="USD",
    )
    karen = _make_employee(
        db,
        first="Karen",
        last="King",
        gender=Gender.FEMALE,
        status=EmploymentStatus.ACTIVE,
        dept_id=sales.id,
        role_id=sales_rep.id,
        level_id=l1.id,
        country_id=us.id,
        hire_date=d(2023, 3, 1),
        salary_amount="50000.00",
        salary_currency="USD",
    )
    leo = _make_employee(
        db,
        first="Leo",
        last="Lee",
        gender=Gender.MALE,
        status=EmploymentStatus.TERMINATED,
        dept_id=sales.id,
        role_id=sales_rep.id,
        level_id=l1.id,
        country_id=us.id,
        hire_date=d(2023, 6, 1),
        salary_amount="55000.00",
        salary_currency="USD",
    )

    db.commit()

    return FixtureIds(
        department_engineering=engineering.id,
        department_sales=sales.id,
        role_swe=swe.id,
        role_sales_rep=sales_rep.id,
        level_l1=l1.id,
        level_l2=l2.id,
        level_l3=l3.id,
        country_us=us.id,
        country_in=india.id,
        alice=alice.id,
        bob=bob.id,
        carol=carol.id,
        dave=dave.id,
        eve=eve.id,
        frank=frank.id,
        grace=grace.id,
        henry=henry.id,
        ivy=ivy.id,
        jack=jack.id,
        karen=karen.id,
        leo=leo.id,
    )
