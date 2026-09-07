"""FX normalisation — converting minor-unit amounts to `BASE_CURRENCY`.

Rates live in `currency_rates(currency, rate_to_base, valid_from)`, seeded as
a static table (see ADR-003-fx-normalisation.md); there is no live feed.
`rate_to_base` means "how many units of the base currency one unit of
`currency` is worth" — e.g. if `BASE_CURRENCY=USD` and `INR.rate_to_base =
0.012`, then 1 INR = 0.012 USD.

`convert_minor_to_base` is the single pure function both the ORM-level
(Python) conversion and the analytics repositories' SQL expressions must
agree with: `amount_base_minor = round(amount_minor * rate_to_base)`. This
module has no DB dependency; `repositories/analytics_repo.py` builds the
equivalent SQL expression (`amount_minor * rate_to_base`, rounded) so
aggregates are computed inside the database, never by pulling rows into
Python and normalising them here.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


class UnknownCurrencyError(ValueError):
    """Raised when no `currency_rates` row exists for a currency."""

    def __init__(self, currency: str) -> None:
        self.currency = currency
        super().__init__(f"No FX rate is known for currency {currency!r}")


def convert_minor_to_base(amount_minor: int, rate_to_base: Decimal) -> int:
    """Convert integer minor units in a foreign currency to base-currency minor units.

    `amount_base_minor = amount_minor * rate_to_base`, rounded HALF_UP to the
    nearest integer minor unit. Both currencies are assumed to use 2 decimal
    places of minor unit (see `services/money.py`), so no extra scaling
    factor is needed — the minor-unit exponent cancels out of the ratio.
    """
    if rate_to_base <= 0:
        raise ValueError(f"rate_to_base must be positive, got {rate_to_base}")
    base = (Decimal(amount_minor) * rate_to_base).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return int(base)


def rates_by_currency(rates: dict[str, Decimal], currency: str) -> Decimal:
    """Look up a currency's rate in a preloaded {currency: rate} map, or raise."""
    try:
        return rates[normalize_lookup_currency(currency)]
    except KeyError:
        raise UnknownCurrencyError(currency) from None


def normalize_lookup_currency(currency: str) -> str:
    return currency.strip().upper()
