"""`/analytics/*` — the compensation-intelligence endpoints.

Every endpoint accepts the same filter facets as `GET /employees`
(`EmployeeFilterParams`), so the dashboard can be scoped to "Engineering in
India" etc. exactly like the employee directory. Endpoint-specific extra
params (`buckets`, `dimension`, ...) are folded into a per-route subclass of
`EmployeeFilterParams` in `schemas/filters.py` rather than declared as a
sibling `Query(...)` parameter — see the comment there for why.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.db.session import DbSession
from app.schemas.analytics import (
    BandHealthOut,
    ByDimensionOut,
    DistributionOut,
    PayEquityOut,
    SummaryOut,
)
from app.schemas.filters import (
    ByDimensionParams,
    DistributionParams,
    EmployeeFilterParams,
    PayEquityParams,
)
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=SummaryOut)
def summary(filters: Annotated[EmployeeFilterParams, Query()], db: DbSession) -> SummaryOut:
    return analytics_service.get_summary(db, filters)


@router.get("/distribution", response_model=DistributionOut)
def distribution(params: Annotated[DistributionParams, Query()], db: DbSession) -> DistributionOut:
    return analytics_service.get_distribution(db, params, params.buckets)


@router.get("/by-dimension", response_model=ByDimensionOut)
def by_dimension(params: Annotated[ByDimensionParams, Query()], db: DbSession) -> ByDimensionOut:
    return analytics_service.get_by_dimension(db, params, params.dimension)


@router.get("/pay-equity", response_model=PayEquityOut)
def pay_equity(params: Annotated[PayEquityParams, Query()], db: DbSession) -> PayEquityOut:
    return analytics_service.get_pay_equity(db, params, min_sample_size=params.min_sample_size)


@router.get("/band-health", response_model=BandHealthOut)
def band_health(filters: Annotated[EmployeeFilterParams, Query()], db: DbSession) -> BandHealthOut:
    return analytics_service.get_band_health(db, filters)
