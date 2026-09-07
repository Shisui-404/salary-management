"""Unit tests for the pure helper functions inside `app.repositories.analytics_repo`
(`_gap_pct`, `_histogram_from_sorted`) — no database. The SQL-driving parts of that
module are covered by `tests/api/test_analytics.py` against a real (temp SQLite)
database, since they are, by design, not meaningfully testable without one.
"""

from app.repositories.analytics_repo import HistogramBucketData, _gap_pct, _histogram_from_sorted


class TestGapPct:
    def test_no_gap(self) -> None:
        assert _gap_pct(100_000, 100_000) == 0.0

    def test_comparison_paid_less_is_positive(self) -> None:
        # reference (male) 64000, comparison (female) 60800 -> comparison paid 5% less
        assert _gap_pct(64_000, 60_800) == 5.0

    def test_comparison_paid_more_is_negative(self) -> None:
        # (60800 - 64000) / 60800 * 100 = -5.263...% -> rounded to 1dp
        assert _gap_pct(60_800, 64_000) == -5.3

    def test_zero_reference_returns_zero_not_a_crash(self) -> None:
        assert _gap_pct(0, 50_000) == 0.0

    def test_rounds_to_one_decimal_place(self) -> None:
        # 100 -> 97 is a 3% gap exactly
        assert _gap_pct(100, 97) == 3.0


class TestHistogramFromSorted:
    def test_empty_input_returns_empty_histogram(self) -> None:
        assert _histogram_from_sorted([], buckets=5) == []

    def test_all_identical_values_collapse_to_one_bucket(self) -> None:
        result = _histogram_from_sorted([100, 100, 100], buckets=5)
        assert result == [HistogramBucketData(100, 100, 3)]

    def test_bucket_count_matches_request(self) -> None:
        values = list(range(0, 100))
        result = _histogram_from_sorted(values, buckets=10)
        assert len(result) == 10

    def test_every_value_is_counted_exactly_once(self) -> None:
        values = [1, 5, 9, 20, 42, 42, 99, 100, 3, 77]
        result = _histogram_from_sorted(values, buckets=5)
        assert sum(b.count for b in result) == len(values)

    def test_buckets_are_contiguous_and_cover_the_range(self) -> None:
        values = list(range(0, 1000, 7))
        result = _histogram_from_sorted(values, buckets=8)
        assert result[0].lower_minor == values[0]
        assert result[-1].upper_minor == values[-1]
        for i in range(len(result) - 1):
            assert result[i].upper_minor == result[i + 1].lower_minor

    def test_single_value_list(self) -> None:
        result = _histogram_from_sorted([42], buckets=5)
        assert result == [HistogramBucketData(42, 42, 1)]

    def test_min_and_max_land_in_first_and_last_bucket(self) -> None:
        values = [0, 10, 20, 30, 40, 50, 100]
        result = _histogram_from_sorted(values, buckets=5)
        assert result[0].count >= 1  # contains the minimum
        assert result[-1].count >= 1  # contains the maximum
