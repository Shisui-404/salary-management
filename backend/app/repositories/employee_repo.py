"""Employee query construction — the one place SQL for `Employee` lives.

`build_employee_query()` is the single source for the joined
employee + current-salary + band + FX-normalised-amount shape used by both
`GET /employees` (list/filter/sort/paginate) and `GET /employees/{id}`
(single row, same shape). Doing this once means the list's `band_position`
filter and the detail view's `band_position` field can never disagree.

Money stays in SQL end-to-end here: base-currency amounts are computed with
`amount_minor * rate_to_base` inside the query (see
`repositories/currency_repo.py`), not by pulling rows into Python and
converting them — this is what lets filtering/sorting by `salary` or
`compa_ratio` and paginating stay index/LIMIT-driven instead of loading the
whole table.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Select, and_, case, func, literal, or_, select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.enums import BandPosition
from app.models.reference import Country, Department, JobRole, Level
from app.models.salary_band import SalaryBand
from app.models.salary_record import SalaryRecord
from app.repositories.currency_repo import latest_rates_subquery
from app.schemas.filters import EmployeeFilterParams
from app.services import money

_SORT_FIELDS = {"name", "salary", "hire_date", "compa_ratio", "department"}


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")


@dataclass(frozen=True)
class EmployeeQueryExpressions:
    """The computed (non-column) SQL expressions shared by SELECT, WHERE and ORDER BY."""

    amount_base_minor: object
    band_min_base_minor: object
    band_mid_base_minor: object
    band_max_base_minor: object
    compa_ratio: object
    band_position: object


def _build_expressions(sr_rate, sb_rate) -> EmployeeQueryExpressions:
    amount_base = func.round(SalaryRecord.amount_minor * sr_rate.c.rate_to_base)
    band_min_base = func.round(SalaryBand.min_minor * sb_rate.c.rate_to_base)
    band_mid_base = func.round(SalaryBand.mid_minor * sb_rate.c.rate_to_base)
    band_max_base = func.round(SalaryBand.max_minor * sb_rate.c.rate_to_base)

    compa_ratio_expr = case(
        (
            and_(SalaryBand.id.isnot(None), band_mid_base > 0, SalaryRecord.id.isnot(None)),
            amount_base / band_mid_base,
        ),
        else_=None,
    )
    band_position_expr = case(
        (SalaryBand.id.is_(None), literal(BandPosition.UNBANDED.value)),
        (amount_base < band_min_base, literal(BandPosition.BELOW.value)),
        (amount_base > band_max_base, literal(BandPosition.ABOVE.value)),
        else_=literal(BandPosition.WITHIN.value),
    )
    return EmployeeQueryExpressions(
        amount_base_minor=amount_base,
        band_min_base_minor=band_min_base,
        band_mid_base_minor=band_mid_base,
        band_max_base_minor=band_max_base,
        compa_ratio=compa_ratio_expr,
        band_position=band_position_expr,
    )


def build_employee_query() -> tuple[Select, EmployeeQueryExpressions]:
    """The full employee + current-salary + band join, with FX-normalised amounts.

    Returns the `Select` (selecting the `Employee` entity plus every joined
    reference/salary/band column needed to build an `EmployeeOut`) alongside
    the raw expressions, so callers can reuse them in `.where()`/`.order_by()`
    without re-deriving the SQL.
    """
    sr_rate = latest_rates_subquery()
    sb_rate = latest_rates_subquery()
    expr = _build_expressions(sr_rate, sb_rate)

    stmt = (
        select(
            Employee,
            Department.id.label("department_id_"),
            Department.name.label("department_name"),
            JobRole.id.label("job_role_id_"),
            JobRole.name.label("job_role_name"),
            Level.id.label("level_id_"),
            Level.name.label("level_name"),
            Level.rank.label("level_rank"),
            Country.id.label("country_id_"),
            Country.name.label("country_name"),
            Country.code.label("country_code"),
            Country.currency.label("country_currency"),
            SalaryRecord.id.label("salary_id"),
            SalaryRecord.amount_minor.label("salary_amount_minor"),
            SalaryRecord.currency.label("salary_currency"),
            SalaryRecord.effective_from.label("salary_effective_from"),
            SalaryRecord.change_reason.label("salary_change_reason"),
            SalaryBand.min_minor.label("band_min_minor"),
            SalaryBand.mid_minor.label("band_mid_minor"),
            SalaryBand.max_minor.label("band_max_minor"),
            SalaryBand.currency.label("band_currency"),
            expr.amount_base_minor.label("amount_base_minor"),
            expr.band_min_base_minor.label("band_min_base_minor"),
            expr.band_mid_base_minor.label("band_mid_base_minor"),
            expr.band_max_base_minor.label("band_max_base_minor"),
            expr.compa_ratio.label("compa_ratio"),
            expr.band_position.label("band_position"),
        )
        .join(Department, Employee.department_id == Department.id)
        .join(JobRole, Employee.job_role_id == JobRole.id)
        .join(Level, Employee.level_id == Level.id)
        .join(Country, Employee.country_id == Country.id)
        .outerjoin(
            SalaryRecord,
            and_(SalaryRecord.employee_id == Employee.id, SalaryRecord.effective_to.is_(None)),
        )
        .outerjoin(sr_rate, sr_rate.c.currency == SalaryRecord.currency)
        .outerjoin(
            SalaryBand,
            and_(
                SalaryBand.job_role_id == Employee.job_role_id,
                SalaryBand.level_id == Employee.level_id,
                SalaryBand.country_id == Employee.country_id,
            ),
        )
        .outerjoin(sb_rate, sb_rate.c.currency == SalaryBand.currency)
    )
    return stmt, expr


def apply_filters(
    stmt: Select, expr: EmployeeQueryExpressions, filters: EmployeeFilterParams
) -> Select:
    """Apply the shared facet filters (search, department/country/role/level, status,
    gender, band position, base-currency salary range) to a statement built from
    `build_employee_query()`."""
    if filters.search:
        term = f"%{_escape_like(filters.search)}%"
        stmt = stmt.where(
            or_(
                Employee.first_name.ilike(term, escape="\\"),
                Employee.last_name.ilike(term, escape="\\"),
                Employee.email.ilike(term, escape="\\"),
                Employee.employee_code.ilike(term, escape="\\"),
            )
        )
    if filters.department_id is not None:
        stmt = stmt.where(Employee.department_id == filters.department_id)
    if filters.country_id is not None:
        stmt = stmt.where(Employee.country_id == filters.country_id)
    if filters.job_role_id is not None:
        stmt = stmt.where(Employee.job_role_id == filters.job_role_id)
    if filters.level_id is not None:
        stmt = stmt.where(Employee.level_id == filters.level_id)
    if filters.employment_status is not None:
        stmt = stmt.where(Employee.employment_status == filters.employment_status)
    if filters.gender is not None:
        stmt = stmt.where(Employee.gender == filters.gender)
    if filters.band_position is not None:
        stmt = stmt.where(expr.band_position == filters.band_position.value)
    if filters.min_salary_base is not None:
        stmt = stmt.where(expr.amount_base_minor >= money.to_minor_units(filters.min_salary_base))
    if filters.max_salary_base is not None:
        stmt = stmt.where(expr.amount_base_minor <= money.to_minor_units(filters.max_salary_base))
    return stmt


def apply_sort(stmt: Select, expr: EmployeeQueryExpressions, sort: str) -> Select:
    """`sort` is one of name|salary|hire_date|compa_ratio|department, optionally
    prefixed with `-` for descending. Unknown values fall back to the default (name asc)
    — the router validates the value shape; this is the last line of defence."""
    descending = sort.startswith("-")
    field = sort[1:] if descending else sort
    if field not in _SORT_FIELDS:
        field = "name"

    column = {
        "name": (Employee.last_name, Employee.first_name),
        "salary": (expr.amount_base_minor,),
        "hire_date": (Employee.hire_date,),
        "compa_ratio": (expr.compa_ratio,),
        "department": (Department.name,),
    }[field]

    if descending:
        return stmt.order_by(*(c.desc() for c in column))
    return stmt.order_by(*column)


def count_matching(db: Session, stmt: Select) -> int:
    """Count rows matching a filtered (but not yet sorted/paginated) statement."""
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    return db.execute(count_stmt).scalar_one()


def get_by_id_row(db: Session, employee_id: int):
    """A single joined row (same shape as the list query) for one employee, or `None`."""
    stmt, _expr = build_employee_query()
    stmt = stmt.where(Employee.id == employee_id)
    return db.execute(stmt).first()


def get_by_email(db: Session, email: str) -> Employee | None:
    return db.execute(select(Employee).where(Employee.email == email)).scalar_one_or_none()


def get_by_employee_code(db: Session, employee_code: str) -> Employee | None:
    return db.execute(
        select(Employee).where(Employee.employee_code == employee_code)
    ).scalar_one_or_none()


def get_employee_or_none(db: Session, employee_id: int) -> Employee | None:
    return db.get(Employee, employee_id)


def count_employees(db: Session) -> int:
    return db.execute(select(func.count()).select_from(Employee)).scalar_one()
