"""Assembles `repositories/analytics_repo` results into the contract's
analytics response DTOs — the only place minor-unit integers become the
decimal strings and rounded percentages the API actually returns.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.repositories import analytics_repo
from app.schemas.analytics import (
    BandHealthOut,
    BandHealthOutlier,
    ByDimensionOut,
    DimensionGroup,
    DistributionOut,
    HistogramBucket,
    PayEquityGroup,
    PayEquityOut,
    PayEquityOverall,
    Percentiles,
    SummaryOut,
)
from app.schemas.filters import EmployeeFilterParams
from app.services import money


def get_summary(db: Session, filters: EmployeeFilterParams) -> SummaryOut:
    base_currency = get_settings().base_currency
    data = analytics_repo.get_summary(db, filters)
    return SummaryOut(
        base_currency=base_currency,
        headcount=data.headcount,
        active_headcount=data.active_headcount,
        total_annual_payroll=money.minor_units_to_str(data.total_annual_payroll_minor),
        mean_salary=money.minor_units_to_str(data.mean_salary_minor),
        median_salary=money.minor_units_to_str(data.median_salary_minor),
        min_salary=money.minor_units_to_str(data.min_salary_minor),
        max_salary=money.minor_units_to_str(data.max_salary_minor),
        countries=data.countries,
        departments=data.departments,
        band_coverage_pct=data.band_coverage_pct,
    )


def get_distribution(db: Session, filters: EmployeeFilterParams, buckets: int) -> DistributionOut:
    base_currency = get_settings().base_currency
    data = analytics_repo.get_distribution(db, filters, buckets)
    p = data.percentiles_minor
    return DistributionOut(
        base_currency=base_currency,
        percentiles=Percentiles(
            p10=money.minor_units_to_str(p.get(0.10) or 0),
            p25=money.minor_units_to_str(p.get(0.25) or 0),
            p50=money.minor_units_to_str(p.get(0.50) or 0),
            p75=money.minor_units_to_str(p.get(0.75) or 0),
            p90=money.minor_units_to_str(p.get(0.90) or 0),
        ),
        histogram=[
            HistogramBucket(
                lower=money.minor_units_to_str(b.lower_minor),
                upper=money.minor_units_to_str(b.upper_minor),
                count=b.count,
            )
            for b in data.histogram
        ],
    )


def get_by_dimension(db: Session, filters: EmployeeFilterParams, dimension: str) -> ByDimensionOut:
    """`dimension` is validated by the router (a `Literal` query param), so any
    value reaching here is already one of `analytics_repo.DIMENSION_COLUMNS`."""
    base_currency = get_settings().base_currency
    groups = analytics_repo.get_by_dimension(db, filters, dimension)
    return ByDimensionOut(
        base_currency=base_currency,
        dimension=dimension,
        groups=[
            DimensionGroup(
                id=g.id,
                name=g.name,
                headcount=g.headcount,
                median=money.minor_units_to_str(g.median_minor),
                mean=money.minor_units_to_str(g.mean_minor),
                p25=money.minor_units_to_str(g.p25_minor),
                p75=money.minor_units_to_str(g.p75_minor),
                min=money.minor_units_to_str(g.min_minor),
                max=money.minor_units_to_str(g.max_minor),
                total_payroll=money.minor_units_to_str(g.total_payroll_minor),
            )
            for g in groups
        ],
    )


def get_pay_equity(
    db: Session, filters: EmployeeFilterParams, *, min_sample_size: int = 5
) -> PayEquityOut:
    base_currency = get_settings().base_currency
    data = analytics_repo.get_pay_equity(db, filters, min_sample_size=min_sample_size)

    overall = None
    if data.overall is not None:
        overall = PayEquityOverall(
            reference="male",
            comparison="female",
            reference_median=money.minor_units_to_str(data.overall.reference_median_minor),
            comparison_median=money.minor_units_to_str(data.overall.comparison_median_minor),
            gap_pct=data.overall.gap_pct,
            sample_reference=data.overall.sample_reference,
            sample_comparison=data.overall.sample_comparison,
        )

    groups = [
        PayEquityGroup(
            key=key,
            job_role=role_name,
            level=level_name,
            reference_median=money.minor_units_to_str(g.reference_median_minor),
            comparison_median=money.minor_units_to_str(g.comparison_median_minor),
            gap_pct=g.gap_pct,
            sample_reference=g.sample_reference,
            sample_comparison=g.sample_comparison,
            sufficient_sample=True,
        )
        for key, role_name, level_name, g in data.groups
    ]

    return PayEquityOut(
        base_currency=base_currency,
        min_sample_size=min_sample_size,
        overall=overall,
        groups=groups,
        suppressed_groups=data.suppressed_groups,
    )


def get_band_health(db: Session, filters: EmployeeFilterParams) -> BandHealthOut:
    base_currency = get_settings().base_currency
    data = analytics_repo.get_band_health(db, filters)
    total = data.below + data.within + data.above + data.unbanded

    def pct(n: int) -> float:
        return round((n / total * 100), 1) if total else 0.0

    return BandHealthOut(
        base_currency=base_currency,
        below=data.below,
        within=data.within,
        above=data.above,
        unbanded=data.unbanded,
        below_pct=pct(data.below),
        within_pct=pct(data.within),
        above_pct=pct(data.above),
        outliers=[
            BandHealthOutlier(
                employee_id=o.employee_id,
                full_name=o.full_name,
                department=o.department,
                job_role=o.job_role,
                level=o.level,
                country=o.country,
                salary_base=money.minor_units_to_str(o.salary_base_minor),
                band_min=money.minor_units_to_str(o.band_min_minor),
                band_max=money.minor_units_to_str(o.band_max_minor),
                compa_ratio=o.compa_ratio,
                position=o.position,
                deviation_pct=o.deviation_pct,
            )
            for o in data.outliers
        ],
    )
