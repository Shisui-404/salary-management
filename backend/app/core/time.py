"""A single `utcnow()` used by every model default, storing naive-but-UTC timestamps.

SQLite's default `DATETIME` type parses stored values with a regex that has
no timezone-offset group; round-tripping a timezone-*aware* datetime through
it is unreliable. Every timestamp column in this app is UTC by convention
(never stored with a tzinfo), and API responses that must render an
ISO-8601 UTC string with a `Z` suffix (e.g. `SalaryRecord.created_at`) add
the `Z` at the serialization boundary instead — see
`schemas/salary.py`.
"""

from __future__ import annotations

import datetime as dt


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC).replace(tzinfo=None)
