"""SalaryRecord: the append-only, effective-dated compensation timeline.

Never UPDATE `amount_minor` in place. A raise is recorded by closing the
currently-open row (`effective_to = new.effective_from - 1 day`) and
inserting a new row with `effective_to = NULL`, both in one transaction —
see `services/salary_service.py`. This is the single source of truth for an
employee's pay history; "current salary" is simply the row where
`effective_to IS NULL`.
"""

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, Enum, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.db.session import Base
from app.models.enums import ChangeReason

if TYPE_CHECKING:
    from app.models.employee import Employee


class SalaryRecord(Base):
    __tablename__ = "salary_records"
    __table_args__ = (
        CheckConstraint("amount_minor >= 0", name="ck_salary_records_amount_non_negative"),
        Index("ix_salary_records_employee_open", "employee_id", "effective_to"),
        # The append-only invariant, enforced by the database rather than
        # merely by convention: an employee may have at most ONE open
        # (`effective_to IS NULL`) salary record. Without this, two
        # concurrent raises can each read the same "current" record before
        # either commits and both insert an open row, leaving the employee
        # with two current salaries -- after which `get_open_record`'s
        # `scalar_one_or_none()` raises and the employee can no longer be
        # given a raise at all. Partial unique indexes are supported by both
        # SQLite (>= 3.8.0) and Postgres, so the guarantee is identical on
        # each. `services/salary_service.py` catches the resulting
        # IntegrityError and returns 409 rather than a 500.
        Index(
            "uq_salary_records_one_open_per_employee",
            "employee_id",
            unique=True,
            sqlite_where=text("effective_to IS NULL"),
            postgresql_where=text("effective_to IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)

    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    effective_from: Mapped[dt.date] = mapped_column(nullable=False)
    effective_to: Mapped[dt.date | None] = mapped_column(nullable=True)

    change_reason: Mapped[ChangeReason] = mapped_column(
        Enum(ChangeReason, native_enum=False, length=30), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(default=utcnow, nullable=False)

    employee: Mapped["Employee"] = relationship(back_populates="salary_records")
