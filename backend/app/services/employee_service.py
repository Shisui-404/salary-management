"""Employee domain logic: CRUD orchestration and building `EmployeeOut` from a
joined repository row.

`row_to_employee_out` is the single place a raw SQL row (see
`repositories/employee_repo.build_employee_query`) is turned into the
contract's `Employee` shape — money formatting, band info and compa-ratio
all funnel through here so the list endpoint and the detail endpoint can
never render an employee differently.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Row
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import DomainValidationError, EmailAlreadyExistsError, EmployeeNotFoundError
from app.models.employee import Employee
from app.models.enums import BandPosition
from app.repositories import employee_repo, reference_repo
from app.schemas.employee import (
    BandInfo,
    CurrentSalary,
    EmployeeCreate,
    EmployeeOut,
    EmployeeUpdate,
)
from app.schemas.reference import CountryRef, LevelRef, RefItem
from app.services import money
from app.services.salary_service import create_initial_salary


def row_to_employee_out(row: Row) -> EmployeeOut:
    base_currency = get_settings().base_currency
    emp: Employee = row[0]

    current_salary = None
    if row.salary_id is not None:
        current_salary = CurrentSalary(
            amount=money.minor_units_to_str(row.salary_amount_minor),
            currency=row.salary_currency,
            amount_base=money.minor_units_to_str(int(row.amount_base_minor)),
            base_currency=base_currency,
            effective_from=row.salary_effective_from,
            change_reason=row.salary_change_reason,
        )

    band = None
    if row.band_min_minor is not None:
        band = BandInfo(
            min=money.minor_units_to_str(int(row.band_min_base_minor)),
            mid=money.minor_units_to_str(int(row.band_mid_base_minor)),
            max=money.minor_units_to_str(int(row.band_max_base_minor)),
            currency=base_currency,
        )

    compa_ratio_val = round(float(row.compa_ratio), 2) if row.compa_ratio is not None else None

    return EmployeeOut(
        id=emp.id,
        employee_code=emp.employee_code,
        first_name=emp.first_name,
        last_name=emp.last_name,
        full_name=emp.full_name,
        email=emp.email,
        gender=emp.gender,
        hire_date=emp.hire_date,
        employment_status=emp.employment_status,
        department=RefItem(id=row.department_id_, name=row.department_name),
        job_role=RefItem(id=row.job_role_id_, name=row.job_role_name),
        level=LevelRef(id=row.level_id_, name=row.level_name, rank=row.level_rank),
        country=CountryRef(
            id=row.country_id_,
            name=row.country_name,
            code=row.country_code,
            currency=row.country_currency,
        ),
        manager_id=emp.manager_id,
        current_salary=current_salary,
        compa_ratio=compa_ratio_val,
        band_position=BandPosition(row.band_position),
        band=band,
    )


def get_employee_out(db: Session, employee_id: int) -> EmployeeOut:
    row = employee_repo.get_by_id_row(db, employee_id)
    if row is None:
        raise EmployeeNotFoundError(employee_id)
    return row_to_employee_out(row)


def _validate_references(
    db: Session,
    *,
    department_id: int | None,
    job_role_id: int | None,
    level_id: int | None,
    country_id: int | None,
    manager_id: int | None,
) -> None:
    errors = []
    if department_id is not None and not reference_repo.department_exists(db, department_id):
        errors.append(
            {"field": "department_id", "message": f"Department {department_id} does not exist"}
        )
    if job_role_id is not None and not reference_repo.job_role_exists(db, job_role_id):
        errors.append({"field": "job_role_id", "message": f"Job role {job_role_id} does not exist"})
    if level_id is not None and not reference_repo.level_exists(db, level_id):
        errors.append({"field": "level_id", "message": f"Level {level_id} does not exist"})
    if country_id is not None and not reference_repo.country_exists(db, country_id):
        errors.append({"field": "country_id", "message": f"Country {country_id} does not exist"})
    if manager_id is not None and employee_repo.get_employee_or_none(db, manager_id) is None:
        errors.append({"field": "manager_id", "message": f"Manager {manager_id} does not exist"})
    if errors:
        raise DomainValidationError("Referenced entity does not exist", details=errors)


@contextmanager
def _translating_email_conflict(db: Session, email: str) -> Iterator[None]:
    """Translate a unique-constraint violation on `email` into the contract's 409.

    `get_by_email` is a read followed by a write, so two concurrent requests
    can both pass that check and collide only when the row actually hits the
    database — which happens at FLUSH (where the id is assigned) as well as at
    COMMIT. Both are covered here, so the loser of the race gets the
    `email_already_exists` the contract promises rather than an unhandled 500.
    """
    try:
        yield
    except IntegrityError as exc:
        db.rollback()
        if "email" in str(exc.orig).lower():
            raise EmailAlreadyExistsError(email) from exc
        raise


def create_employee(db: Session, data: EmployeeCreate) -> EmployeeOut:
    if employee_repo.get_by_email(db, str(data.email)) is not None:
        raise EmailAlreadyExistsError(str(data.email))

    _validate_references(
        db,
        department_id=data.department_id,
        job_role_id=data.job_role_id,
        level_id=data.level_id,
        country_id=data.country_id,
        manager_id=data.manager_id,
    )

    employee = Employee(
        employee_code="",  # placeholder, set below once the id is known
        first_name=data.first_name,
        last_name=data.last_name,
        email=str(data.email),
        gender=data.gender,
        hire_date=data.hire_date,
        employment_status=data.employment_status,
        department_id=data.department_id,
        job_role_id=data.job_role_id,
        level_id=data.level_id,
        country_id=data.country_id,
        manager_id=data.manager_id,
    )
    with _translating_email_conflict(db, str(data.email)):
        db.add(employee)
        db.flush()  # assigns employee.id

        employee.employee_code = f"ACME-{employee.id:06d}"

        if data.initial_salary is not None:
            create_initial_salary(
                db,
                employee_id=employee.id,
                amount=data.initial_salary.amount,
                currency=data.initial_salary.currency,
                effective_from=data.hire_date,
            )

        db.commit()

    return get_employee_out(db, employee.id)


def update_employee(db: Session, employee_id: int, data: EmployeeUpdate) -> EmployeeOut:
    employee = employee_repo.get_employee_or_none(db, employee_id)
    if employee is None:
        raise EmployeeNotFoundError(employee_id)

    fields = data.model_dump(exclude_unset=True)

    if "email" in fields and fields["email"] != employee.email:
        existing = employee_repo.get_by_email(db, fields["email"])
        if existing is not None and existing.id != employee_id:
            raise EmailAlreadyExistsError(fields["email"])

    _validate_references(
        db,
        department_id=fields.get("department_id"),
        job_role_id=fields.get("job_role_id"),
        level_id=fields.get("level_id"),
        country_id=fields.get("country_id"),
        manager_id=fields.get("manager_id"),
    )

    if "manager_id" in fields and fields["manager_id"] == employee_id:
        raise DomainValidationError(
            "An employee cannot be their own manager",
            details=[{"field": "manager_id", "message": "cannot equal the employee's own id"}],
        )

    for field_name, value in fields.items():
        setattr(employee, field_name, value)

    with _translating_email_conflict(db, fields.get("email", employee.email)):
        db.commit()

    return get_employee_out(db, employee_id)
