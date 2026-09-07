"""Money as integer minor units + ISO-4217 currency code — see ADR-001.

No float is ever allowed to touch a monetary amount. Every boundary crossing
(parsing an incoming decimal string, serialising an outgoing one, converting
between currencies) goes through this module with explicit `Decimal` math and
`ROUND_HALF_UP` quantisation, so rounding behaviour is a single, unit-tested
fact rather than something scattered across services.

All amounts in this system use two decimal places of minor unit (cents,
paise, ...). Real-world ISO-4217 has currencies with 0 or 3 decimal digits
(JPY, BHD); this system deliberately standardises on 2 for every currency to
keep the schema and the arithmetic uniform, which is a documented
simplification (ADR-001) appropriate for a compensation system that is not
issuing payments.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

MINOR_UNITS_EXPONENT = 2
MINOR_UNITS_FACTOR = 10**MINOR_UNITS_EXPONENT
_QUANT = Decimal(1).scaleb(-MINOR_UNITS_EXPONENT)  # Decimal("0.01")

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


class InvalidMoneyError(ValueError):
    """A malformed amount string or an invalid ISO-4217 currency code."""


def normalize_currency(currency: str) -> str:
    """Upper-case and validate a currency code is a 3-letter ISO-4217 shape.

    This checks the *shape* (three letters), not membership in a specific
    known-currency list — the seeded set of real currencies used by the app
    lives in the `countries`/`currency_rates` tables, and "not a currency we
    have a rate for" is a separate, FX-layer concern (see `fx.py`).
    """
    code = (currency or "").strip().upper()
    if not _CURRENCY_RE.match(code):
        raise InvalidMoneyError(f"{currency!r} is not a valid 3-letter ISO-4217 currency code")
    return code


def parse_amount(amount: str | Decimal | int) -> Decimal:
    """Parse input into a `Decimal`, rejecting NaN/Infinity and garbage strings.

    Does not quantise to minor units — call `to_minor_units` for that.
    """
    try:
        value = amount if isinstance(amount, Decimal) else Decimal(str(amount))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise InvalidMoneyError(f"{amount!r} is not a valid decimal amount") from exc
    if not value.is_finite():
        raise InvalidMoneyError(f"{amount!r} is not a finite amount")
    return value


def to_minor_units(amount: str | Decimal | int) -> int:
    """Quantise a decimal amount to 2dp (ROUND_HALF_UP) and return integer minor units."""
    quantised = parse_amount(amount).quantize(_QUANT, rounding=ROUND_HALF_UP)
    return int(quantised * MINOR_UNITS_FACTOR)


def minor_units_to_decimal(amount_minor: int) -> Decimal:
    """Convert integer minor units back to a 2dp `Decimal` amount."""
    return (Decimal(amount_minor) / MINOR_UNITS_FACTOR).quantize(_QUANT, rounding=ROUND_HALF_UP)


def minor_units_to_str(amount_minor: int) -> str:
    """Convert integer minor units to the contract's decimal-string form, e.g. "2400000.00"."""
    return f"{minor_units_to_decimal(amount_minor):.2f}"


@dataclass(frozen=True, slots=True)
class Money:
    """A validated (amount_minor, currency) pair — the in-process value object.

    Construct via `Money.from_decimal(...)`; the bare constructor assumes
    `amount_minor` is already correctly quantised (e.g. read back from the
    database) and only normalises/validates the currency code.
    """

    amount_minor: int
    currency: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "currency", normalize_currency(self.currency))

    @classmethod
    def from_decimal(cls, amount: str | Decimal | int, currency: str) -> Money:
        return cls(amount_minor=to_minor_units(amount), currency=normalize_currency(currency))

    def as_decimal(self) -> Decimal:
        return minor_units_to_decimal(self.amount_minor)

    def as_str(self) -> str:
        return minor_units_to_str(self.amount_minor)

    def __add__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        if other.currency != self.currency:
            raise InvalidMoneyError(
                f"Cannot add {self.currency} and {other.currency} without conversion"
            )
        return Money(self.amount_minor + other.amount_minor, self.currency)


def percent_change(old_minor: int, new_minor: int) -> Decimal | None:
    """Percentage change from `old_minor` to `new_minor`, rounded to 1dp.

    Returns `None` when `old_minor` is zero (change is undefined/infinite).
    Matches the contract's `change_pct` semantics: positive means an
    increase, in the record's own local currency (no FX conversion here).
    """
    if old_minor == 0:
        return None
    pct = (Decimal(new_minor - old_minor) / Decimal(old_minor)) * 100
    return pct.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
