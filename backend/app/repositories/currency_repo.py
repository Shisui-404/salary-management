"""Currency-rate queries — the "latest rate per currency" building block.

`currency_rates` can in principle hold more than one dated row per currency
(the schema has `valid_from` for exactly that reason), so every consumer —
Python-side FX conversion and the SQL join used by the list/analytics
queries — resolves to the row with the greatest `valid_from` per currency,
never just "the first row for this currency".
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.selectable import Subquery

from app.models.currency_rate import CurrencyRate


def latest_rates_subquery() -> Subquery:
    """A `(currency, rate_to_base)` subquery holding only the newest row per currency.

    Call this once per join in a larger query — each call returns an
    independent `Subquery`/`Select` object, so the same currency table can be
    joined twice (e.g. once for a salary's currency, once for a band's) in a
    single statement.
    """
    latest_dates = (
        select(
            CurrencyRate.currency,
            func.max(CurrencyRate.valid_from).label("valid_from"),
        )
        .group_by(CurrencyRate.currency)
        .subquery()
    )
    return (
        select(CurrencyRate.currency, CurrencyRate.rate_to_base)
        .join(
            latest_dates,
            and_(
                CurrencyRate.currency == latest_dates.c.currency,
                CurrencyRate.valid_from == latest_dates.c.valid_from,
            ),
        )
        .subquery()
    )


def get_all_latest_rates(db: Session) -> dict[str, Decimal]:
    """All currencies' latest rate, as a plain {currency: rate} dict for Python-side use."""
    sub = latest_rates_subquery()
    rows = db.execute(select(sub.c.currency, sub.c.rate_to_base)).all()
    return {row.currency: row.rate_to_base for row in rows}


def get_rate(db: Session, currency: str, as_of: dt.date | None = None) -> Decimal | None:
    """The latest rate for one currency, or `None` if unknown. `as_of` is currently
    unused (rates are not point-in-time in this seeded dataset) but kept in the
    signature so an as-of lookup can be added without changing callers."""
    stmt = select(CurrencyRate.rate_to_base).where(CurrencyRate.currency == currency)
    stmt = stmt.order_by(CurrencyRate.valid_from.desc()).limit(1)
    return db.execute(stmt).scalar_one_or_none()
