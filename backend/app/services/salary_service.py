"""Salary-revision domain logic — the append-only, effective-dated invariant.

`record_salary_change` is the only way a `SalaryRecord` is created after an
employee's initial one: it validates the new effective date, closes the
currently open record, and inserts the new one — all inside the caller's
existing `Session` transaction (routers commit once per request; nothing
here calls `commit()` itself, so a validation failure leaves nothing
half-applied).
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import EmployeeNotFoundError, SalaryEffectiveDateInvalidError
from app.models.enums import ChangeReason
from app.models.salary_record import SalaryRecord
from app.repositories import employee_repo, salary_repo
from app.schemas.salary import SalaryRecordOut
from app.services import fx, money


def create_initial_salary(
    db: Session, *, employee_id: int, amount: str, currency: str, effective_from: dt.date
) -> SalaryRecord:
    """Used only when creating a new employee with an `initial_salary` — there is no
    open record yet, so there is nothing to close."""
    m = money.Money.from_decimal(amount, currency)
    return salary_repo.insert_record(
        db,
        employee_id=employee_id,
        amount_minor=m.amount_minor,
        currency=m.currency,
        effective_from=effective_from,
        change_reason=ChangeReason.INITIAL,
        note=None,
    )


def record_salary_change(
    db: Session,
    *,
    employee_id: int,
    amount: str,
    currency: str,
    effective_from: dt.date,
    change_reason: ChangeReason,
    note: str | None,
) -> SalaryRecord:
    """Close the currently open salary record and open a new one, atomically.

    Raises `EmployeeNotFoundError` if the employee doesn't exist, and
    `SalaryEffectiveDateInvalidError` if `effective_from` is not strictly
    after the current record's `effective_from` — this also implicitly
    rejects backdated and overlapping revisions.
    """
    if employee_repo.get_employee_or_none(db, employee_id) is None:
        raise EmployeeNotFoundError(employee_id)

    current = salary_repo.get_open_record(db, employee_id)
    m = money.Money.from_decimal(amount, currency)

    if current is not None:
        if effective_from <= current.effective_from:
            raise SalaryEffectiveDateInvalidError(
                f"effective_from ({effective_from.isoformat()}) must be strictly after the "
                f"current record's effective_from ({current.effective_from.isoformat()})"
            )
        salary_repo.close_record(current, effective_to=effective_from - dt.timedelta(days=1))

    return salary_repo.insert_record(
        db,
        employee_id=employee_id,
        amount_minor=m.amount_minor,
        currency=m.currency,
        effective_from=effective_from,
        change_reason=change_reason,
        note=note,
    )


def get_salary_history_with_change_pct(
    db: Session, employee_id: int
) -> list[tuple[SalaryRecord, Decimal | None]]:
    """Full salary timeline (newest first), each paired with its `change_pct` —
    the percentage change over the immediately *preceding* record in local
    currency, or `None` for the first record or when the currency changed
    between the two records (a percentage across currencies is meaningless).
    """
    records = salary_repo.get_history(db, employee_id)  # newest first
    chronological = list(reversed(records))

    change_pct_by_id: dict[int, Decimal | None] = {}
    previous: SalaryRecord | None = None
    for rec in chronological:
        if previous is None or previous.currency != rec.currency:
            change_pct_by_id[rec.id] = None
        else:
            change_pct_by_id[rec.id] = money.percent_change(previous.amount_minor, rec.amount_minor)
        previous = rec

    return [(rec, change_pct_by_id[rec.id]) for rec in records]


def to_salary_record_out(
    record: SalaryRecord,
    change_pct: Decimal | None,
    rates: dict[str, Decimal],
    base_currency: str,
) -> SalaryRecordOut:
    """Build the contract's `SalaryRecord` shape, including the FX-normalised
    `amount_base` — every record in the history is normalised individually,
    each in its own local currency, exactly as `CurrentSalary` is."""
    rate = fx.rates_by_currency(rates, record.currency)
    amount_base_minor = fx.convert_minor_to_base(record.amount_minor, rate)
    return SalaryRecordOut(
        id=record.id,
        employee_id=record.employee_id,
        amount=money.minor_units_to_str(record.amount_minor),
        currency=record.currency,
        amount_base=money.minor_units_to_str(amount_base_minor),
        base_currency=base_currency,
        effective_from=record.effective_from,
        effective_to=record.effective_to,
        change_reason=record.change_reason,
        note=record.note,
        created_at=record.created_at,
        change_pct=float(change_pct) if change_pct is not None else None,
    )
