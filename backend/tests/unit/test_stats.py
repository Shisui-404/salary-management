"""Unit tests for `app.services.stats` — percentile/median/mean, no database.

`percentile_cont` is the SQLite fallback for Postgres's `percentile_cont`
aggregate; these tests pin down the exact linear-interpolation values so a
future change can't silently drift the two implementations apart.
"""

from decimal import Decimal

import pytest

from app.services.stats import mean, median, percentile_cont, round_money


class TestPercentileCont:
    def test_empty_returns_none(self) -> None:
        assert percentile_cont([], 0.5) is None

    def test_single_value_returns_that_value_for_any_p(self) -> None:
        assert percentile_cont([42], 0.0) == Decimal(42)
        assert percentile_cont([42], 0.5) == Decimal(42)
        assert percentile_cont([42], 1.0) == Decimal(42)

    def test_p0_is_min_and_p1_is_max(self) -> None:
        values = [10, 20, 30, 40]
        assert percentile_cont(values, 0.0) == Decimal(10)
        assert percentile_cont(values, 1.0) == Decimal(40)

    def test_median_even_count_averages_middle_two(self) -> None:
        # n=4, p=0.5 -> rank = 0.5*3 = 1.5 -> interpolate values[1], values[2]
        assert percentile_cont([10, 20, 30, 40], 0.5) == Decimal("25")

    def test_median_odd_count_is_middle_value(self) -> None:
        assert percentile_cont([10, 20, 30], 0.5) == Decimal("20")

    def test_all_ties(self) -> None:
        assert percentile_cont([5, 5, 5, 5], 0.5) == Decimal(5)

    def test_known_interpolation(self) -> None:
        # n=5 -> rank = 0.25*4 = 1.0 exactly -> values[1]
        assert percentile_cont([1, 2, 3, 4, 5], 0.25) == Decimal(2)
        # rank = 0.75*4 = 3.0 exactly -> values[3]
        assert percentile_cont([1, 2, 3, 4, 5], 0.75) == Decimal(4)

    def test_fractional_rank_interpolates(self) -> None:
        # n=3 -> p=0.25 -> rank = 0.25*2 = 0.5 -> midpoint of values[0], values[1]
        assert percentile_cont([10, 20, 30], 0.25) == Decimal("15")

    @pytest.mark.parametrize("bad_p", [-0.1, 1.1, 2.0])
    def test_out_of_range_p_raises(self, bad_p: float) -> None:
        with pytest.raises(ValueError, match="p must be"):
            percentile_cont([1, 2, 3], bad_p)

    def test_negative_values(self) -> None:
        assert percentile_cont([-30, -20, -10], 0.5) == Decimal("-20")


class TestMedian:
    def test_delegates_to_percentile_50(self) -> None:
        assert median([1, 2, 3, 4]) == Decimal("2.5")

    def test_empty_returns_none(self) -> None:
        assert median([]) is None


class TestMean:
    def test_basic(self) -> None:
        assert mean([10, 20, 30]) == Decimal(20)

    def test_empty_returns_none(self) -> None:
        assert mean([]) is None

    def test_exact_decimal_division(self) -> None:
        # 10/3 is not exact in binary float but Decimal keeps precision
        result = mean([10, 10, 10, 0, 0, 0])
        assert result == Decimal(5)

    def test_single_value(self) -> None:
        assert mean([7]) == Decimal(7)


class TestRoundMoney:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (Decimal("100.4"), 100),
            (Decimal("100.5"), 101),
            (Decimal("100.49"), 100),
            (Decimal("-100.5"), -101),
            (Decimal("0"), 0),
        ],
    )
    def test_rounds_half_up(self, value: Decimal, expected: int) -> None:
        assert round_money(value) == expected
