"""Unit tests for `app.services.bands` — compa-ratio and band classification."""

from decimal import Decimal

import pytest

from app.models.enums import BandPosition
from app.services.bands import classify_band_position, compa_ratio, deviation_pct


class TestCompaRatio:
    def test_exact_midpoint_is_one(self) -> None:
        assert compa_ratio(100_000, 100_000) == Decimal("1.00")

    def test_below_midpoint(self) -> None:
        assert compa_ratio(48_000, 100_000) == Decimal("0.48")

    def test_above_midpoint(self) -> None:
        assert compa_ratio(150_000, 100_000) == Decimal("1.50")

    def test_zero_mid_returns_none(self) -> None:
        assert compa_ratio(50_000, 0) is None

    def test_negative_mid_returns_none(self) -> None:
        assert compa_ratio(50_000, -1000) is None

    def test_zero_salary(self) -> None:
        assert compa_ratio(0, 100_000) == Decimal("0.00")

    def test_rounds_to_two_dp(self) -> None:
        # 29000 / 29583.333.. isn't exact; verify HALF_UP rounding behaviour
        assert compa_ratio(29_000, 30_000) == Decimal("0.97")  # 0.9666... -> 0.97


class TestClassifyBandPosition:
    def test_within_band_inclusive_of_min(self) -> None:
        assert classify_band_position(100, 100, 200) == BandPosition.WITHIN

    def test_within_band_inclusive_of_max(self) -> None:
        assert classify_band_position(200, 100, 200) == BandPosition.WITHIN

    def test_within_band_strictly_inside(self) -> None:
        assert classify_band_position(150, 100, 200) == BandPosition.WITHIN

    def test_below_band(self) -> None:
        assert classify_band_position(99, 100, 200) == BandPosition.BELOW

    def test_above_band(self) -> None:
        assert classify_band_position(201, 100, 200) == BandPosition.ABOVE

    @pytest.mark.parametrize(
        ("min_", "max_"),
        [(None, 200), (100, None), (None, None)],
    )
    def test_missing_band_is_unbanded(self, min_: int | None, max_: int | None) -> None:
        assert classify_band_position(150, min_, max_) == BandPosition.UNBANDED


class TestDeviationPct:
    def test_within_band_is_zero(self) -> None:
        assert deviation_pct(150, 100, 200) == Decimal("0.0")

    def test_below_band_is_negative(self) -> None:
        # 48000 vs band_min 80000 -> -40.0%
        assert deviation_pct(48_000, 80_000, 120_000) == Decimal("-40.0")

    def test_above_band_is_positive(self) -> None:
        assert deviation_pct(240_000, 80_000, 120_000) == Decimal("100.0")

    def test_at_edges_is_zero(self) -> None:
        assert deviation_pct(100, 100, 200) == Decimal("0.0")
        assert deviation_pct(200, 100, 200) == Decimal("0.0")
