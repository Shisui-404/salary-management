"""Percentile / median math — the SQLite fallback for Postgres's `percentile_cont`.

`repositories/analytics_repo.py` uses the database's own `percentile_cont`
function when the dialect supports it (Postgres). SQLite has no such
function, so for that dialect the repository fetches **only the single,
already-ordered salary column** (never full employee rows) and this module
computes the same linear-interpolation percentile in Python. This isolation
is the point: the fallback is an explicit, narrow, documented path — not an
accidental "load everything into Python" shortcut.

The interpolation method mirrors Postgres's `percentile_cont`: for a
0-indexed sorted sequence of length `n`, the p-th percentile (0 <= p <= 1)
sits at rank `p * (n - 1)`, linearly interpolated between its floor and
ceiling index.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal


def percentile_cont(sorted_values: Sequence[int], p: float) -> Decimal | None:
    """Continuous percentile (linear interpolation) of a sequence sorted ascending.

    `sorted_values` must already be sorted; this function does not sort (the
    SQL fallback path selects `ORDER BY amount ASC`, so re-sorting in Python
    would be redundant work at 10k rows).
    """
    if not sorted_values:
        return None
    if not 0 <= p <= 1:
        raise ValueError(f"p must be within [0, 1], got {p}")

    n = len(sorted_values)
    if n == 1:
        return Decimal(sorted_values[0])

    rank = Decimal(str(p)) * (n - 1)
    lower_idx = int(rank.to_integral_value(rounding=ROUND_FLOOR))
    upper_idx = min(lower_idx + 1, n - 1)
    fraction = rank - lower_idx

    lower_val = Decimal(sorted_values[lower_idx])
    upper_val = Decimal(sorted_values[upper_idx])
    return lower_val + fraction * (upper_val - lower_val)


def median(sorted_values: Sequence[int]) -> Decimal | None:
    """Median = the 50th percentile."""
    return percentile_cont(sorted_values, 0.5)


def mean(values: Sequence[int]) -> Decimal | None:
    """Arithmetic mean, using exact `Decimal` division (28 significant digits)."""
    if not values:
        return None
    return Decimal(sum(values)) / Decimal(len(values))


def round_money(value: Decimal) -> int:
    """Round a Decimal (already in minor units) to the nearest integer minor unit."""
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))
