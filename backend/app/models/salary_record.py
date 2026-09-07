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

from sqlalchemy import BigInteger, CheckConstraint, Enum, ForeignKey, Index, String, Text
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
        # Partial-index intent: on Postgres this could be
        # `Index(..., postgresql_where=text("effective_to IS NULL"))` to make
        # "find the open record" an index-only scan. SQLite (our default
        # here) does not need the predicate to still use the index
        # effectively at this scale, so a plain composite index is used for
        # portability across both dialects.
        Index("ix_salary_records_employee_open", "employee_id", "effective_to"),
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
