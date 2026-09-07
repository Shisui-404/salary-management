"""SalaryRecord persistence primitives.

Deliberately minimal and mechanical: every primitive here does exactly one
thing (fetch the open record, close a record, insert a record). The
transactional invariant — "closing the old record and inserting the new one
happens atomically, and only after the new date is validated" — lives in
`services/salary_service.py`, which composes these primitives inside one
`Session` transaction.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import ChangeReason
from app.models.salary_record import SalaryRecord


def get_open_record(
    db: Session, employee_id: int, *, for_update: bool = False
) -> SalaryRecord | None:
    """The employee's current salary record, or None if they have never had one.

    `for_update` takes a row lock so a concurrent raise for the same employee
    blocks until this transaction finishes, instead of reading the same
    "current" record and racing to replace it. On Postgres this emits
    `SELECT ... FOR UPDATE`; SQLite has no row-level locking and serialises
    write transactions instead, so SQLAlchemy omits the clause there. The
    partial unique index on `salary_records` is the backstop that makes the
    invariant hold on both.
    """
    stmt = select(SalaryRecord).where(
        SalaryRecord.employee_id == employee_id, SalaryRecord.effective_to.is_(None)
    )
    if for_update:
        stmt = stmt.with_for_update()
    return db.execute(stmt).scalar_one_or_none()


def get_history(db: Session, employee_id: int) -> list[SalaryRecord]:
    """Full salary timeline for one employee, newest `effective_from` first."""
    stmt = (
        select(SalaryRecord)
        .where(SalaryRecord.employee_id == employee_id)
        .order_by(SalaryRecord.effective_from.desc(), SalaryRecord.id.desc())
    )
    return list(db.execute(stmt).scalars().all())


def close_record(record: SalaryRecord, effective_to: dt.date) -> None:
    record.effective_to = effective_to


def insert_record(
    db: Session,
    *,
    employee_id: int,
    amount_minor: int,
    currency: str,
    effective_from: dt.date,
    change_reason: ChangeReason,
    note: str | None,
) -> SalaryRecord:
    record = SalaryRecord(
        employee_id=employee_id,
        amount_minor=amount_minor,
        currency=currency,
        effective_from=effective_from,
        effective_to=None,
        change_reason=change_reason,
        note=note,
    )
    db.add(record)
    db.flush()
    return record
