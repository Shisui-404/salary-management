"""Unit tests for `app.services.money` — pure functions, no database.

Money correctness is the single most important property of this codebase
(the domain brief is literally "no floats for money, ever"), so every
rounding edge and every rejection path is exercised here.
"""

from decimal import Decimal

import pytest

from app.services.money import (
    InvalidMoneyError,
    Money,
    minor_units_to_decimal,
    minor_units_to_str,
    normalize_currency,
    parse_amount,
    percent_change,
    to_minor_units,
)


class TestNormalizeCurrency:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("usd", "USD"),
            ("USD", "USD"),
            (" inr ", "INR"),
            ("gBp", "GBP"),
        ],
    )
    def test_valid_codes_are_uppercased_and_trimmed(self, raw: str, expected: str) -> None:
        assert normalize_currency(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        ["", "US", "USDD", "12A", "US$", None],
    )
    def test_invalid_codes_raise(self, raw: str | None) -> None:
        with pytest.raises(InvalidMoneyError):
            normalize_currency(raw)  # type: ignore[arg-type]


class TestParseAmount:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("100", Decimal("100")),
            ("100.5", Decimal("100.5")),
            (0, Decimal("0")),
            (Decimal("1.23"), Decimal("1.23")),
            ("-50.00", Decimal("-50.00")),
        ],
    )
    def test_valid_inputs(self, raw, expected) -> None:
        assert parse_amount(raw) == expected

    @pytest.mark.parametrize("raw", ["not-a-number", "", "1,000", "NaN", "Infinity", "-Infinity"])
    def test_invalid_inputs_raise(self, raw: str) -> None:
        with pytest.raises(InvalidMoneyError):
            parse_amount(raw)


class TestToMinorUnits:
    @pytest.mark.parametrize(
        ("raw", "expected_minor"),
        [
            ("2400000.00", 240_000_000),
            ("0", 0),
            ("0.00", 0),
            ("0.01", 1),
            ("100", 10_000),
            # ROUND_HALF_UP, not banker's rounding: .005 always rounds away from zero.
            ("1.005", 101),
            ("1.015", 102),
            ("1.025", 103),
            ("2.675", 268),
            # negative amounts round the same way (magnitude rounds up, sign preserved)
            ("-1.005", -101),
        ],
    )
    def test_rounding(self, raw: str, expected_minor: int) -> None:
        assert to_minor_units(raw) == expected_minor

    def test_more_than_two_decimals_is_quantised_not_truncated(self) -> None:
        assert to_minor_units("10.999") == 1100  # rounds up to 11.00, not 10.99


class TestMinorUnitsToStr:
    @pytest.mark.parametrize(
        ("minor", "expected"),
        [
            (240_000_000, "2400000.00"),
            (0, "0.00"),
            (1, "0.01"),
            (-150, "-1.50"),
        ],
    )
    def test_formatting(self, minor: int, expected: str) -> None:
        assert minor_units_to_str(minor) == expected

    def test_round_trip_is_exact(self) -> None:
        for raw in ["12345.67", "0.00", "999999999.99", "-42.50"]:
            assert minor_units_to_str(to_minor_units(raw)) == raw


class TestMinorUnitsToDecimal:
    def test_returns_two_dp_decimal(self) -> None:
        assert minor_units_to_decimal(12345) == Decimal("123.45")


class TestMoney:
    def test_from_decimal_normalises_currency(self) -> None:
        m = Money.from_decimal("2400000.00", "inr")
        assert m.amount_minor == 240_000_000
        assert m.currency == "INR"
        assert m.as_str() == "2400000.00"
        assert m.as_decimal() == Decimal("2400000.00")

    def test_rejects_invalid_currency(self) -> None:
        with pytest.raises(InvalidMoneyError):
            Money.from_decimal("100.00", "US")

    def test_is_immutable(self) -> None:
        m = Money.from_decimal("1.00", "USD")
        with pytest.raises(AttributeError):
            m.amount_minor = 200  # type: ignore[misc]

    def test_add_same_currency(self) -> None:
        a = Money.from_decimal("10.00", "USD")
        b = Money.from_decimal("5.50", "USD")
        result = a + b
        assert result.as_str() == "15.50"

    def test_add_different_currency_raises(self) -> None:
        a = Money.from_decimal("10.00", "USD")
        b = Money.from_decimal("5.50", "INR")
        with pytest.raises(InvalidMoneyError):
            _ = a + b

    def test_zero_amount_is_valid(self) -> None:
        m = Money.from_decimal("0", "USD")
        assert m.amount_minor == 0
        assert m.as_str() == "0.00"

    def test_negative_amount_is_parseable(self) -> None:
        # Money itself is a generic value object and does not forbid negative
        # amounts (e.g. a delta); domain-level non-negativity for a *salary*
        # is enforced at the Pydantic schema / DB CHECK constraint layer.
        m = Money.from_decimal("-100.00", "USD")
        assert m.amount_minor == -10_000


class TestPercentChange:
    @pytest.mark.parametrize(
        ("old", "new", "expected"),
        [
            (100_000, 112_500, Decimal("12.5")),
            (100_000, 100_000, Decimal("0.0")),
            (100_000, 90_000, Decimal("-10.0")),
            (200_000, 100_000, Decimal("-50.0")),
        ],
    )
    def test_computed_change(self, old: int, new: int, expected: Decimal) -> None:
        assert percent_change(old, new) == expected

    def test_zero_old_amount_returns_none(self) -> None:
        assert percent_change(0, 100_000) is None

    def test_first_record_has_no_predecessor_is_caller_concern(self) -> None:
        # percent_change itself always needs both endpoints; callers pass
        # `None` through untouched when there is no preceding record.
        assert percent_change(0, 0) is None
