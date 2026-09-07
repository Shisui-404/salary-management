"""Salary-band math: compa-ratio and below/within/above/unbanded classification.

Both functions operate purely on base-currency minor units so they are
identical whether called from Python (single-employee detail view) or
mirrored in SQL for the band-health aggregate (see
`repositories/analytics_repo.py`).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.models.enums import BandPosition

_COMPA_QUANT = Decimal("0.01")


def compa_ratio(salary_base_minor: int, band_mid_base_minor: int) -> Decimal | None:
    """`salary / band_mid`, rounded to 2dp. `None` when the band has no midpoint
    (unbanded, or a malformed band with mid <= 0)."""
    if band_mid_base_minor <= 0:
        return None
    ratio = Decimal(salary_base_minor) / Decimal(band_mid_base_minor)
    return ratio.quantize(_COMPA_QUANT, rounding=ROUND_HALF_UP)


def classify_band_position(
    salary_base_minor: int,
    band_min_base_minor: int | None,
    band_max_base_minor: int | None,
) -> BandPosition:
    """Classify a salary against a band's [min, max] range, inclusive of the edges."""
    if band_min_base_minor is None or band_max_base_minor is None:
        return BandPosition.UNBANDED
    if salary_base_minor < band_min_base_minor:
        return BandPosition.BELOW
    if salary_base_minor > band_max_base_minor:
        return BandPosition.ABOVE
    return BandPosition.WITHIN


def deviation_pct(
    salary_base_minor: int, band_min_base_minor: int, band_max_base_minor: int
) -> Decimal:
    """Percentage deviation from the *nearest* band edge.

    Negative when below the band, positive when above it, `0` when within.
    Used to rank band-health outliers by "how far out of band" they are.
    """
    if salary_base_minor < band_min_base_minor:
        edge = band_min_base_minor
    elif salary_base_minor > band_max_base_minor:
        edge = band_max_base_minor
    else:
        return Decimal("0.0")
    pct = (Decimal(salary_base_minor - edge) / Decimal(edge)) * 100
    return pct.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
