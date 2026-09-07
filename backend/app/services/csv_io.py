"""CSV import/export for the employee directory.

Export produces one row per employee matching the current filter (see
`repositories/employee_repo`), with money already formatted as decimal
strings — never floats.

Import is intentionally scoped to employee *attributes*. An
`salary_amount`/`salary_currency` column pair is honoured only when
*creating* a brand-new employee (matched by neither `employee_code` nor
`email`) — it becomes that employee's `initial` salary record. Updating an
*existing* employee's salary through a bulk import is deliberately
unsupported: the domain rule "salary is append-only and effective-dated"
holds everywhere, and silently overwriting a compensation figure from a
spreadsheet row with no history would violate it. Use
`POST /employees/{id}/salary` for a real, dated revision.

`validate_row` is pure (no DB) and does field-shape validation only
(required fields, enum membership, date/amount parsing); resolving
department/job-role/level/country *names* to ids and upserting the row
requires the database and lives in `import_csv` below.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.employee import Employee
from app.models.enums import EmploymentStatus, Gender
from app.repositories import employee_repo, reference_repo
from app.services import money
from app.services.employee_service import row_to_employee_out
from app.services.salary_service import create_initial_salary

EXPORT_FIELDS = [
    "employee_code",
    "first_name",
    "last_name",
    "email",
    "gender",
    "hire_date",
    "employment_status",
    "department",
    "job_role",
    "level",
    "country",
    "manager_id",
    "salary_amount",
    "salary_currency",
    "salary_amount_base",
    "base_currency",
    "compa_ratio",
    "band_position",
]

IMPORT_REQUIRED_FIELDS = (
    "first_name",
    "last_name",
    "email",
    "gender",
    "hire_date",
    "department",
    "job_role",
    "level",
    "country",
)


@dataclass(frozen=True)
class RowError:
    row: int
    field: str
    message: str


@dataclass(frozen=True)
class ParsedRow:
    employee_code: str | None
    first_name: str
    last_name: str
    email: str
    gender: Gender
    hire_date: dt.date
    employment_status: EmploymentStatus
    department: str
    job_role: str
    level: str
    country: str
    manager_employee_code: str | None
    salary_amount: str | None
    salary_currency: str | None


@dataclass
class ImportResultData:
    total_rows: int
    created: int
    updated: int
    failed: int
    errors: list[RowError]


def _clean(raw: dict[str, str | None], field_name: str) -> str:
    return (raw.get(field_name) or "").strip()


def validate_row(
    raw: dict[str, str | None], row_number: int
) -> tuple[ParsedRow | None, list[RowError]]:
    """Field-shape validation for one CSV row. No database access.

    Returns `(parsed_row, [])` on success or `(None, errors)` on failure —
    never a partially-parsed row, so a caller can never accidentally act on
    invalid data.
    """
    errors: list[RowError] = []

    for required in IMPORT_REQUIRED_FIELDS:
        if not _clean(raw, required):
            errors.append(RowError(row_number, required, "This field is required"))

    email = _clean(raw, "email")
    if email:
        local, _, domain = email.partition("@")
        if not local or not domain or "." not in domain:
            errors.append(RowError(row_number, "email", f"{email!r} is not a valid email address"))

    gender: Gender | None = None
    gender_raw = _clean(raw, "gender")
    if gender_raw:
        try:
            gender = Gender(gender_raw)
        except ValueError:
            errors.append(RowError(row_number, "gender", f"{gender_raw!r} is not a valid gender"))

    hire_date: dt.date | None = None
    hire_date_raw = _clean(raw, "hire_date")
    if hire_date_raw:
        try:
            hire_date = dt.date.fromisoformat(hire_date_raw)
        except ValueError:
            errors.append(
                RowError(
                    row_number, "hire_date", f"{hire_date_raw!r} is not a valid YYYY-MM-DD date"
                )
            )

    status_raw = _clean(raw, "employment_status") or EmploymentStatus.ACTIVE.value
    employment_status: EmploymentStatus | None = None
    try:
        employment_status = EmploymentStatus(status_raw)
    except ValueError:
        errors.append(
            RowError(
                row_number,
                "employment_status",
                f"{status_raw!r} is not a valid employment status",
            )
        )

    salary_amount_raw = _clean(raw, "salary_amount")
    salary_currency_raw = _clean(raw, "salary_currency")
    salary_amount: str | None = None
    salary_currency: str | None = None
    if salary_amount_raw or salary_currency_raw:
        if not (salary_amount_raw and salary_currency_raw):
            errors.append(
                RowError(
                    row_number,
                    "salary_amount",
                    "salary_amount and salary_currency must both be provided together",
                )
            )
        else:
            try:
                money.parse_amount(salary_amount_raw)
                salary_amount = salary_amount_raw
            except money.InvalidMoneyError as exc:
                errors.append(RowError(row_number, "salary_amount", str(exc)))
            try:
                salary_currency = money.normalize_currency(salary_currency_raw)
            except money.InvalidMoneyError as exc:
                errors.append(RowError(row_number, "salary_currency", str(exc)))

    if errors:
        return None, errors

    return (
        ParsedRow(
            employee_code=_clean(raw, "employee_code") or None,
            first_name=_clean(raw, "first_name"),
            last_name=_clean(raw, "last_name"),
            email=email,
            gender=gender,  # type: ignore[arg-type]
            hire_date=hire_date,  # type: ignore[arg-type]
            employment_status=employment_status,  # type: ignore[arg-type]
            department=_clean(raw, "department"),
            job_role=_clean(raw, "job_role"),
            level=_clean(raw, "level"),
            country=_clean(raw, "country"),
            manager_employee_code=_clean(raw, "manager_employee_code") or None,
            salary_amount=salary_amount,
            salary_currency=salary_currency,
        ),
        [],
    )


def _resolve_references(db: Session, parsed: ParsedRow, row_number: int):
    errors: list[RowError] = []
    department = reference_repo.get_department_by_name(db, parsed.department)
    if department is None:
        errors.append(
            RowError(row_number, "department", f"Unknown department {parsed.department!r}")
        )
    job_role = reference_repo.get_job_role_by_name(db, parsed.job_role)
    if job_role is None:
        errors.append(RowError(row_number, "job_role", f"Unknown job role {parsed.job_role!r}"))
    level = reference_repo.get_level_by_name(db, parsed.level)
    if level is None:
        errors.append(RowError(row_number, "level", f"Unknown level {parsed.level!r}"))
    country = reference_repo.get_country_by_name(db, parsed.country)
    if country is None:
        errors.append(RowError(row_number, "country", f"Unknown country {parsed.country!r}"))

    manager = None
    if parsed.manager_employee_code:
        manager = employee_repo.get_by_employee_code(db, parsed.manager_employee_code)
        if manager is None:
            errors.append(
                RowError(
                    row_number,
                    "manager_employee_code",
                    f"Unknown manager employee_code {parsed.manager_employee_code!r}",
                )
            )
    return department, job_role, level, country, manager, errors


def import_csv(db: Session, file_content: bytes) -> ImportResultData:
    text = file_content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    total_rows = 0
    created = 0
    updated = 0
    failed = 0
    errors: list[RowError] = []

    for row_number, raw in enumerate(reader, start=1):
        total_rows += 1
        parsed, row_errors = validate_row(raw, row_number)
        if row_errors:
            errors.extend(row_errors)
            failed += 1
            continue

        department, job_role, level, country, manager, ref_errors = _resolve_references(
            db, parsed, row_number
        )
        if ref_errors:
            errors.extend(ref_errors)
            failed += 1
            continue

        existing = None
        if parsed.employee_code:
            existing = employee_repo.get_by_employee_code(db, parsed.employee_code)
        if existing is None:
            existing = employee_repo.get_by_email(db, parsed.email)

        try:
            with db.begin_nested():
                if existing is not None:
                    if parsed.email != existing.email:
                        conflict = employee_repo.get_by_email(db, parsed.email)
                        if conflict is not None and conflict.id != existing.id:
                            raise ValueError(
                                f"Email {parsed.email!r} already used by another employee"
                            )
                    existing.first_name = parsed.first_name
                    existing.last_name = parsed.last_name
                    existing.email = parsed.email
                    existing.gender = parsed.gender
                    existing.hire_date = parsed.hire_date
                    existing.employment_status = parsed.employment_status
                    existing.department_id = department.id
                    existing.job_role_id = job_role.id
                    existing.level_id = level.id
                    existing.country_id = country.id
                    existing.manager_id = manager.id if manager else None
                    db.flush()
                else:
                    employee = Employee(
                        employee_code="",
                        first_name=parsed.first_name,
                        last_name=parsed.last_name,
                        email=parsed.email,
                        gender=parsed.gender,
                        hire_date=parsed.hire_date,
                        employment_status=parsed.employment_status,
                        department_id=department.id,
                        job_role_id=job_role.id,
                        level_id=level.id,
                        country_id=country.id,
                        manager_id=manager.id if manager else None,
                    )
                    db.add(employee)
                    db.flush()
                    employee.employee_code = f"ACME-{employee.id:06d}"
                    if parsed.salary_amount is not None and parsed.salary_currency is not None:
                        create_initial_salary(
                            db,
                            employee_id=employee.id,
                            amount=parsed.salary_amount,
                            currency=parsed.salary_currency,
                            effective_from=parsed.hire_date,
                        )
        except Exception as exc:  # noqa: BLE001 - one bad row must not sink the batch
            errors.append(RowError(row_number, "_row", str(exc)))
            failed += 1
            continue

        if existing is not None:
            updated += 1
        else:
            created += 1

    db.commit()
    return ImportResultData(
        total_rows=total_rows, created=created, updated=updated, failed=failed, errors=errors
    )


def export_csv(db: Session, stmt) -> str:
    """Render every row of an already-filtered employee statement as CSV text."""
    base_currency = get_settings().base_currency
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=EXPORT_FIELDS)
    writer.writeheader()

    for row in db.execute(stmt):
        out = row_to_employee_out(row)
        writer.writerow(
            {
                "employee_code": out.employee_code,
                "first_name": out.first_name,
                "last_name": out.last_name,
                "email": out.email,
                "gender": out.gender.value,
                "hire_date": out.hire_date.isoformat(),
                "employment_status": out.employment_status.value,
                "department": out.department.name,
                "job_role": out.job_role.name,
                "level": out.level.name,
                "country": out.country.name,
                "manager_id": out.manager_id if out.manager_id is not None else "",
                "salary_amount": out.current_salary.amount if out.current_salary else "",
                "salary_currency": out.current_salary.currency if out.current_salary else "",
                "salary_amount_base": out.current_salary.amount_base if out.current_salary else "",
                "base_currency": base_currency,
                "compa_ratio": out.compa_ratio if out.compa_ratio is not None else "",
                "band_position": out.band_position.value,
            }
        )
    return buffer.getvalue()
