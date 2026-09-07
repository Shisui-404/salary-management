"""SQL for the five `/analytics/*` endpoints.

Every aggregate here starts from the *same* filtered employee set that
`GET /employees` uses (`employee_repo.build_employee_query` +
`apply_filters`, wrapped as a subquery), so a filtered dashboard figure and
a filtered employee list are always describing the same rows, with the same
FX-normalised amounts and the same band-position classification.

**Percentiles.** Postgres computes them in SQL via `percentile_cont`, a
single aggregate query, no rows pulled into Python. SQLite has no such
function; for that dialect this module fetches **only the narrow column(s)
actually needed** — never full employee rows — already ordered by the
database, and computes the same linear-interpolation percentile in Python
via `services/stats.percentile_cont`. `_fetch_sorted_amounts` (single
column: the salary) backs `summary`/`distribution`; `_fetch_grouped_amounts`
(two narrow columns: a group key + the salary) backs the per-group medians
in `by-dimension` and `pay-equity`, which are inherently grouped and so need
the key alongside the value. Both are isolated, single-purpose queries, not
an incidental "load everything" shortcut.
"""

from __future__ import annotations

import bisect
from collections import defaultdict
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import ColumnElement, case, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.selectable import Subquery

from app.models.enums import BandPosition, EmploymentStatus, Gender
from app.repositories import employee_repo
from app.schemas.filters import EmployeeFilterParams
from app.services import stats

DIMENSION_COLUMNS = {
    "department": ("department_id", "department_name"),
    "country": ("country_id", "country_name"),
    "job_role": ("job_role_id", "job_role_name"),
    "level": ("level_id", "level_name"),
}

_DEFAULT_PERCENTILES = (0.10, 0.25, 0.50, 0.75, 0.90)


def _supports_percentile_cont(db: Session) -> bool:
    return db.get_bind().dialect.name == "postgresql"


def filtered_subquery(filters: EmployeeFilterParams) -> Subquery:
    stmt, expr = employee_repo.build_employee_query()
    stmt = employee_repo.apply_filters(stmt, expr, filters)
    return stmt.subquery()


def _as_decimal(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _fetch_sorted_amounts(
    db: Session, column: ColumnElement, extra_where: ColumnElement | None = None
) -> list[int]:
    """The SQLite fallback's one allowed full-column fetch: only `column`,
    already ordered ascending by the database. Never add another column here."""
    stmt = select(column).where(column.is_not(None))
    if extra_where is not None:
        stmt = stmt.where(extra_where)
    stmt = stmt.order_by(column)
    return list(db.execute(stmt).scalars().all())


def _fetch_grouped_amounts(db: Session, key_col: ColumnElement, amount_col: ColumnElement) -> dict:
    """SQLite fallback for *per-group* percentiles: fetch (group_key, amount)
    pairs — exactly the two narrow columns needed — ordered by group then
    amount, and bucket them in Python. Mirrors `_fetch_sorted_amounts`,
    keyed by group."""
    stmt = select(key_col, amount_col).where(amount_col.is_not(None)).order_by(key_col, amount_col)
    grouped: dict = defaultdict(list)
    for key, amount in db.execute(stmt):
        grouped[key].append(amount)
    return grouped


def percentiles(
    db: Session, sub: Subquery, ps: tuple[float, ...] = _DEFAULT_PERCENTILES
) -> dict[float, int | None]:
    """{p: amount_base_minor} for the given percentiles, over `sub.c.amount_base_minor`."""
    col = sub.c.amount_base_minor
    if _supports_percentile_cont(db):
        cols = [func.percentile_cont(p).within_group(col).label(f"p{i}") for i, p in enumerate(ps)]
        row = db.execute(select(*cols).select_from(sub).where(col.is_not(None))).one()
        return {
            p: (stats.round_money(_as_decimal(row[i])) if row[i] is not None else None)
            for i, p in enumerate(ps)
        }
    values = _fetch_sorted_amounts(db, col)
    result = {}
    for p in ps:
        v = stats.percentile_cont(values, p)
        result[p] = stats.round_money(v) if v is not None else None
    return result


@dataclass
class SummaryData:
    headcount: int
    active_headcount: int
    total_annual_payroll_minor: int
    mean_salary_minor: int
    median_salary_minor: int
    min_salary_minor: int
    max_salary_minor: int
    countries: int
    departments: int
    band_coverage_pct: float


def get_summary(db: Session, filters: EmployeeFilterParams) -> SummaryData:
    sub = filtered_subquery(filters)
    amt = sub.c.amount_base_minor

    # One aggregate query over the (expensive, multi-join) filtered subquery
    # rather than three separate ones -- each execution re-walks the full
    # employee+salary+band+FX join, so cutting three round trips to one is a
    # meaningful win at 10k rows (see the perf numbers in backend/README.md).
    agg = db.execute(
        select(
            func.count(),
            func.count().filter(sub.c.employment_status == EmploymentStatus.ACTIVE.value),
            func.sum(amt),
            func.min(amt),
            func.max(amt),
            func.count(amt),
            func.count(func.distinct(sub.c.country_id)),
            func.count(func.distinct(sub.c.department_id)),
            func.count().filter(sub.c.band_position != BandPosition.UNBANDED.value),
        ).select_from(sub)
    ).one()
    (
        headcount,
        active_headcount,
        total_payroll,
        min_amt,
        max_amt,
        salaried_count,
        countries,
        departments,
        banded,
    ) = agg

    total_payroll = int(total_payroll or 0)
    mean_minor = (
        stats.round_money(Decimal(total_payroll) / Decimal(salaried_count)) if salaried_count else 0
    )
    median_minor = percentiles(db, sub, (0.5,)).get(0.5) or 0
    band_coverage_pct = round((banded / headcount * 100), 1) if headcount else 0.0

    return SummaryData(
        headcount=headcount,
        active_headcount=active_headcount,
        total_annual_payroll_minor=total_payroll,
        mean_salary_minor=mean_minor,
        median_salary_minor=median_minor,
        min_salary_minor=int(min_amt or 0),
        max_salary_minor=int(max_amt or 0),
        countries=countries,
        departments=departments,
        band_coverage_pct=band_coverage_pct,
    )


@dataclass
class HistogramBucketData:
    lower_minor: int
    upper_minor: int
    count: int


@dataclass
class DistributionData:
    percentiles_minor: dict[float, int | None]
    histogram: list[HistogramBucketData]


def _histogram_from_sorted(values: list[int], buckets: int) -> list[HistogramBucketData]:
    if not values:
        return []
    lo, hi = values[0], values[-1]
    if lo == hi:
        return [HistogramBucketData(lo, hi, len(values))]

    span = hi - lo
    edges = [lo + (span * i) // buckets for i in range(buckets + 1)]
    edges[-1] = hi  # guard against integer-division drift losing the max value
    counts = [0] * buckets
    for v in values:
        idx = bisect.bisect_right(edges, v) - 1
        idx = min(max(idx, 0), buckets - 1)
        counts[idx] += 1
    return [HistogramBucketData(edges[i], edges[i + 1], counts[i]) for i in range(buckets)]


def get_distribution(db: Session, filters: EmployeeFilterParams, buckets: int) -> DistributionData:
    sub = filtered_subquery(filters)
    col = sub.c.amount_base_minor
    pct = percentiles(db, sub)

    if _supports_percentile_cont(db):
        min_amt, max_amt = db.execute(
            select(func.min(col), func.max(col)).where(col.is_not(None))
        ).one()
        histogram = _histogram_via_sql(db, sub, col, min_amt, max_amt, buckets)
    else:
        values = _fetch_sorted_amounts(db, col)
        histogram = _histogram_from_sorted(values, buckets)

    return DistributionData(percentiles_minor=pct, histogram=histogram)


def _histogram_via_sql(db, sub, col, min_amt, max_amt, buckets: int) -> list[HistogramBucketData]:
    """Postgres path: `width_bucket` computes the bucket index in SQL, one GROUP BY query."""
    if min_amt is None or max_amt is None:
        return []
    if min_amt == max_amt:
        count = db.execute(select(func.count()).select_from(sub).where(col == min_amt)).scalar_one()
        return [HistogramBucketData(int(min_amt), int(max_amt), count)]

    bucket_idx = func.width_bucket(col, min_amt, max_amt, buckets)
    rows = db.execute(
        select(bucket_idx.label("idx"), func.count())
        .select_from(sub)
        .where(col.is_not(None))
        .group_by(bucket_idx)
    ).all()
    counts_by_idx = {int(idx): count for idx, count in rows}

    span = max_amt - min_amt
    edges = [min_amt + (span * i) // buckets for i in range(buckets + 1)]
    edges[-1] = max_amt
    return [
        HistogramBucketData(edges[i], edges[i + 1], counts_by_idx.get(i + 1, 0))
        for i in range(buckets)
    ]


@dataclass
class DimensionGroupData:
    id: int
    name: str
    headcount: int
    median_minor: int
    mean_minor: int
    p25_minor: int
    p75_minor: int
    min_minor: int
    max_minor: int
    total_payroll_minor: int


def get_by_dimension(
    db: Session, filters: EmployeeFilterParams, dimension: str
) -> list[DimensionGroupData]:
    sub = filtered_subquery(filters)
    id_col_name, name_col_name = DIMENSION_COLUMNS[dimension]
    id_col = sub.c[id_col_name]
    name_col = sub.c[name_col_name]
    amt = sub.c.amount_base_minor

    base_rows = db.execute(
        select(
            id_col.label("id"),
            name_col.label("name"),
            func.count().label("headcount"),
            func.count(amt).label("salaried_count"),
            func.sum(amt).label("total_payroll"),
            func.min(amt).label("min_amt"),
            func.max(amt).label("max_amt"),
        )
        .select_from(sub)
        .group_by(id_col, name_col)
        .order_by(func.count().desc())
    ).all()

    if _supports_percentile_cont(db):
        pct_rows = db.execute(
            select(
                id_col.label("id"),
                func.percentile_cont(0.5).within_group(amt).label("median"),
                func.percentile_cont(0.25).within_group(amt).label("p25"),
                func.percentile_cont(0.75).within_group(amt).label("p75"),
            )
            .select_from(sub)
            .where(amt.is_not(None))
            .group_by(id_col)
        ).all()
        pct_by_id = {r.id: (r.median, r.p25, r.p75) for r in pct_rows}
    else:
        grouped = _fetch_grouped_amounts(db, id_col, amt)
        pct_by_id = {
            gid: (
                stats.percentile_cont(vals, 0.5),
                stats.percentile_cont(vals, 0.25),
                stats.percentile_cont(vals, 0.75),
            )
            for gid, vals in grouped.items()
        }

    groups = []
    for row in base_rows:
        median, p25, p75 = pct_by_id.get(row.id, (None, None, None))
        salaried = row.salaried_count or 0
        total_payroll = int(row.total_payroll or 0)
        mean_minor = (
            stats.round_money(Decimal(total_payroll) / Decimal(salaried)) if salaried else 0
        )
        groups.append(
            DimensionGroupData(
                id=row.id,
                name=row.name,
                headcount=row.headcount,
                median_minor=stats.round_money(_as_decimal(median)) if median is not None else 0,
                mean_minor=mean_minor,
                p25_minor=stats.round_money(_as_decimal(p25)) if p25 is not None else 0,
                p75_minor=stats.round_money(_as_decimal(p75)) if p75 is not None else 0,
                min_minor=int(row.min_amt or 0),
                max_minor=int(row.max_amt or 0),
                total_payroll_minor=total_payroll,
            )
        )
    return groups


@dataclass
class PayEquityGroupStats:
    reference_median_minor: int
    comparison_median_minor: int
    gap_pct: float
    sample_reference: int
    sample_comparison: int


@dataclass
class PayEquityData:
    overall: PayEquityGroupStats | None
    groups: list[tuple[str, str, str, PayEquityGroupStats]]  # (key, job_role, level, stats)
    suppressed_groups: int


def _gap_pct(reference_median: int, comparison_median: int) -> float:
    if reference_median == 0:
        return 0.0
    pct = (Decimal(reference_median - comparison_median) / Decimal(reference_median)) * 100
    return float(pct.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def get_pay_equity(
    db: Session,
    filters: EmployeeFilterParams,
    *,
    reference: str = Gender.MALE.value,
    comparison: str = Gender.FEMALE.value,
    min_sample_size: int = 5,
) -> PayEquityData:
    sub = filtered_subquery(filters)
    amt = sub.c.amount_base_minor

    # Narrow fetch: role id/name, level id/name, gender, amount — the minimum
    # columns needed to build per-(role, level, gender) sorted amount lists.
    stmt = (
        select(
            sub.c.job_role_id,
            sub.c.job_role_name,
            sub.c.level_id,
            sub.c.level_name,
            sub.c.gender,
            amt,
        )
        .where(amt.is_not(None))
        .where(sub.c.gender.in_([reference, comparison]))
        .order_by(sub.c.job_role_id, sub.c.level_id, sub.c.gender, amt)
    )

    overall_values: dict[str, list[int]] = {reference: [], comparison: []}
    grouped: dict[tuple[int, str, int, str], dict[str, list[int]]] = defaultdict(
        lambda: {reference: [], comparison: []}
    )
    for role_id, role_name, level_id, level_name, gender, amount in db.execute(stmt):
        overall_values[gender].append(amount)
        grouped[(role_id, role_name, level_id, level_name)][gender].append(amount)

    overall = None
    # `overall_values` concatenates many per-(role, level) runs that are each
    # individually ascending (the query orders by role, level, gender, then
    # amount) but the concatenation across roles/levels is NOT globally
    # sorted — `stats.median` requires a fully sorted sequence, so sort here
    # rather than relying on the query's (differently-scoped) ordering.
    ref_vals, comp_vals = sorted(overall_values[reference]), sorted(overall_values[comparison])
    if ref_vals and comp_vals:
        ref_median = stats.round_money(stats.median(ref_vals))
        comp_median = stats.round_money(stats.median(comp_vals))
        overall = PayEquityGroupStats(
            reference_median_minor=ref_median,
            comparison_median_minor=comp_median,
            gap_pct=_gap_pct(ref_median, comp_median),
            sample_reference=len(ref_vals),
            sample_comparison=len(comp_vals),
        )

    groups: list[tuple[str, str, str, PayEquityGroupStats]] = []
    suppressed = 0
    for (_role_id, role_name, _level_id, level_name), by_gender in sorted(
        grouped.items(), key=lambda kv: (kv[0][1], kv[0][3])
    ):
        r_vals, c_vals = by_gender[reference], by_gender[comparison]
        if len(r_vals) < min_sample_size or len(c_vals) < min_sample_size:
            suppressed += 1
            continue
        # Each bucket's lists are already ascending (query order_by ends in
        # `amt` within a fixed role/level/gender), but sort defensively so
        # this doesn't silently break if the query's ordering ever changes.
        r_vals, c_vals = sorted(r_vals), sorted(c_vals)
        r_median = stats.round_money(stats.median(r_vals))
        c_median = stats.round_money(stats.median(c_vals))
        groups.append(
            (
                f"{role_name} · {level_name}",
                role_name,
                level_name,
                PayEquityGroupStats(
                    reference_median_minor=r_median,
                    comparison_median_minor=c_median,
                    gap_pct=_gap_pct(r_median, c_median),
                    sample_reference=len(r_vals),
                    sample_comparison=len(c_vals),
                ),
            )
        )

    return PayEquityData(overall=overall, groups=groups, suppressed_groups=suppressed)


@dataclass
class BandHealthOutlierData:
    employee_id: int
    full_name: str
    department: str
    job_role: str
    level: str
    country: str
    salary_base_minor: int
    band_min_minor: int
    band_max_minor: int
    compa_ratio: float
    position: str
    deviation_pct: float


@dataclass
class BandHealthData:
    below: int
    within: int
    above: int
    unbanded: int
    outliers: list[BandHealthOutlierData]


def get_band_health(db: Session, filters: EmployeeFilterParams) -> BandHealthData:
    sub = filtered_subquery(filters)

    counts = dict(
        db.execute(
            select(sub.c.band_position, func.count()).select_from(sub).group_by(sub.c.band_position)
        ).all()
    )
    below = counts.get(BandPosition.BELOW.value, 0)
    within = counts.get(BandPosition.WITHIN.value, 0)
    above = counts.get(BandPosition.ABOVE.value, 0)
    unbanded = counts.get(BandPosition.UNBANDED.value, 0)

    deviation_expr = case(
        (
            sub.c.amount_base_minor < sub.c.band_min_base_minor,
            (sub.c.amount_base_minor - sub.c.band_min_base_minor)
            * 100.0
            / sub.c.band_min_base_minor,
        ),
        (
            sub.c.amount_base_minor > sub.c.band_max_base_minor,
            (sub.c.amount_base_minor - sub.c.band_max_base_minor)
            * 100.0
            / sub.c.band_max_base_minor,
        ),
        else_=0.0,
    )

    outlier_rows = db.execute(
        select(
            sub.c.id,
            sub.c.first_name,
            sub.c.last_name,
            sub.c.department_name,
            sub.c.job_role_name,
            sub.c.level_name,
            sub.c.country_code,
            sub.c.amount_base_minor,
            sub.c.band_min_base_minor,
            sub.c.band_max_base_minor,
            sub.c.compa_ratio,
            sub.c.band_position,
            deviation_expr.label("deviation_pct"),
        )
        .select_from(sub)
        .where(sub.c.band_position.in_([BandPosition.BELOW.value, BandPosition.ABOVE.value]))
        .order_by(func.abs(deviation_expr).desc())
        .limit(20)
    ).all()

    outliers = [
        BandHealthOutlierData(
            employee_id=row.id,
            full_name=f"{row.first_name} {row.last_name}",
            department=row.department_name,
            job_role=row.job_role_name,
            level=row.level_name,
            country=row.country_code,
            salary_base_minor=int(row.amount_base_minor),
            band_min_minor=int(row.band_min_base_minor),
            band_max_minor=int(row.band_max_base_minor),
            compa_ratio=round(float(row.compa_ratio), 2) if row.compa_ratio is not None else 0.0,
            position=row.band_position,
            deviation_pct=round(float(row.deviation_pct), 1),
        )
        for row in outlier_rows
    ]

    return BandHealthData(
        below=below, within=within, above=above, unbanded=unbanded, outliers=outliers
    )
