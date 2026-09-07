"""Shared Pydantic validators for incoming money fields.

Rejecting a malformed or negative amount here, at the schema boundary,
means it becomes a clean `422 validation_error` (via FastAPI's
`RequestValidationError` handler) instead of reaching the database's
`CHECK (amount_minor >= 0)` constraint and surfacing as an unhandled 500.
"""

from __future__ import annotations

from app.services import money


def validate_salary_amount(value: str) -> str:
    """A salary amount must parse as a valid decimal and be non-negative.
    Returns the original string unchanged (validation only) so the exact
    user-supplied precision still reaches `money.to_minor_units` later."""
    try:
        parsed = money.parse_amount(value)
    except money.InvalidMoneyError as exc:
        raise ValueError(str(exc)) from exc
    if parsed < 0:
        raise ValueError(f"amount must not be negative, got {value!r}")
    return value
