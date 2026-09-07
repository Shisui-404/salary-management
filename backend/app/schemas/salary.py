"""Salary-record request/response DTOs — the effective-dated compensation timeline."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field, field_serializer

from app.models.enums import ChangeReason


class SalaryRecordOut(BaseModel):
    id: int
    employee_id: int
    amount: str
    currency: str
    amount_base: str
    base_currency: str
    effective_from: dt.date
    effective_to: dt.date | None
    change_reason: ChangeReason
    note: str | None
    created_at: dt.datetime
    change_pct: float | None

    @field_serializer("created_at")
    def _serialize_created_at(self, value: dt.datetime) -> str:
        # `created_at` is stored naive-but-UTC (see core/time.py); render the
        # contract's ISO-8601 UTC form with a trailing `Z` here rather than
        # relying on the DB round-trip to preserve a tzinfo it never had.
        if value.tzinfo is None:
            value = value.replace(tzinfo=dt.UTC)
        return value.isoformat().replace("+00:00", "Z")


class SalaryHistoryOut(BaseModel):
    items: list[SalaryRecordOut]


class SalaryCreateIn(BaseModel):
    amount: str
    currency: str = Field(min_length=3, max_length=3)
    effective_from: dt.date
    change_reason: ChangeReason
    note: str | None = None
