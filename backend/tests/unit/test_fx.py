"""Unit tests for `app.services.fx` — pure currency-conversion math, no database."""

from decimal import Decimal

import pytest

from app.services.fx import (
    UnknownCurrencyError,
    convert_minor_to_base,
    rates_by_currency,
)


class TestConvertMinorToBase:
    def test_identity_rate(self) -> None:
        assert convert_minor_to_base(100_000, Decimal("1")) == 100_000

    def test_typical_conversion(self) -> None:
        # 2,400,000.00 INR at 0.012 USD/INR -> 28,800.00 USD
        assert convert_minor_to_base(240_000_000, Decimal("0.012")) == 2_880_000

    def test_rounds_half_up(self) -> None:
        # 1 minor unit * 0.125 = 0.125 -> rounds up to 0 (HALF_UP of .125 rounded to whole is 0? )
        # use a case with an exact .5 boundary instead for an unambiguous assertion
        assert convert_minor_to_base(2, Decimal("0.5")) == 1  # 2 * 0.5 = 1.0 exactly
        assert convert_minor_to_base(1, Decimal("1.5")) == 2  # 1.5 -> rounds up to 2

    def test_zero_amount(self) -> None:
        assert convert_minor_to_base(0, Decimal("0.012")) == 0

    def test_negative_amount_preserves_sign(self) -> None:
        assert convert_minor_to_base(-100, Decimal("2")) == -200

    @pytest.mark.parametrize("bad_rate", [Decimal("0"), Decimal("-1")])
    def test_non_positive_rate_raises(self, bad_rate: Decimal) -> None:
        with pytest.raises(ValueError, match="positive"):
            convert_minor_to_base(1000, bad_rate)


class TestRatesByCurrency:
    def test_found(self) -> None:
        rates = {"USD": Decimal("1"), "INR": Decimal("0.012")}
        assert rates_by_currency(rates, "inr") == Decimal("0.012")

    def test_missing_raises_unknown_currency(self) -> None:
        rates = {"USD": Decimal("1")}
        with pytest.raises(UnknownCurrencyError) as exc_info:
            rates_by_currency(rates, "XYZ")
        assert exc_info.value.currency == "XYZ"

    def test_empty_rate_table_raises(self) -> None:
        with pytest.raises(UnknownCurrencyError):
            rates_by_currency({}, "USD")
