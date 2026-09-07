"""Analytics response DTOs — one per `/analytics/*` endpoint in the contract.

All monetary figures here are already normalised to `base_currency`; see
`repositories/analytics_repo.py` for the SQL that does the normalisation.
"""

from __future__ import annotations

from pydantic import BaseModel


class SummaryOut(BaseModel):
    base_currency: str
    headcount: int
    active_headcount: int
    total_annual_payroll: str
    mean_salary: str
    median_salary: str
    min_salary: str
    max_salary: str
    countries: int
    departments: int
    band_coverage_pct: float


class Percentiles(BaseModel):
    p10: str
    p25: str
    p50: str
    p75: str
    p90: str


class HistogramBucket(BaseModel):
    lower: str
    upper: str
    count: int


class DistributionOut(BaseModel):
    base_currency: str
    percentiles: Percentiles
    histogram: list[HistogramBucket]


class DimensionGroup(BaseModel):
    id: int
    name: str
    headcount: int
    median: str
    mean: str
    p25: str
    p75: str
    min: str
    max: str
    total_payroll: str


class ByDimensionOut(BaseModel):
    base_currency: str
    dimension: str
    groups: list[DimensionGroup]


class PayEquityOverall(BaseModel):
    reference: str
    comparison: str
    reference_median: str
    comparison_median: str
    gap_pct: float
    sample_reference: int
    sample_comparison: int


class PayEquityGroup(BaseModel):
    key: str
    job_role: str
    level: str
    reference_median: str
    comparison_median: str
    gap_pct: float
    sample_reference: int
    sample_comparison: int
    sufficient_sample: bool


class PayEquityOut(BaseModel):
    base_currency: str
    min_sample_size: int
    overall: PayEquityOverall | None
    groups: list[PayEquityGroup]
    suppressed_groups: int


class BandHealthOutlier(BaseModel):
    employee_id: int
    full_name: str
    department: str
    job_role: str
    level: str
    country: str
    salary_base: str
    band_min: str
    band_max: str
    compa_ratio: float
    position: str
    deviation_pct: float


class BandHealthOut(BaseModel):
    base_currency: str
    below: int
    within: int
    above: int
    unbanded: int
    below_pct: float
    within_pct: float
    above_pct: float
    outliers: list[BandHealthOutlier]
