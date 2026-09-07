"""CSV import result DTO — per-row validation report, no partial silent failures."""

from __future__ import annotations

from pydantic import BaseModel


class ImportRowError(BaseModel):
    row: int
    field: str
    message: str


class ImportResult(BaseModel):
    total_rows: int
    created: int
    updated: int
    failed: int
    errors: list[ImportRowError]
