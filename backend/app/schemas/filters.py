"""Shared query-parameter models for employee filtering.

`GET /employees`, `GET /employees/export` and every `/analytics/*` endpoint
accept the same filter facets (contract: "all accept the same filter params
as `GET /employees`"). Declaring them once here — as a FastAPI "query
parameter model" (`Annotated[Model, Query()]`) — keeps the filter contract
identical across every endpoint instead of hand-copying query params five
times.

`model_config` deliberately does not set `extra="forbid"`: the contract says
"Unknown query params are ignored", so extra params are silently dropped
rather than raising 422.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BandPosition, EmploymentStatus, Gender


class EmployeeFilterParams(BaseModel):
    model_config = ConfigDict(extra="ignore")

    search: str | None = None
    department_id: int | None = None
    country_id: int | None = None
    job_role_id: int | None = None
    level_id: int | None = None
    employment_status: EmploymentStatus | None = None
    gender: Gender | None = None
    band_position: BandPosition | None = None
    min_salary_base: Decimal | None = None
    max_salary_base: Decimal | None = None


class EmployeeListParams(EmployeeFilterParams):
    sort: str = "name"
    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


# FastAPI only flattens a `Annotated[BaseModel, Query()]` parameter into
# individual query params when it is the *sole* query-typed parameter on the
# route (see `fastapi.dependencies.utils._get_flat_fields_from_params`,
# which flattens only `len(fields) == 1`). Mixing a filters model with a
# sibling plain `Query(...)` parameter on the same route silently breaks
# that flattening. So every analytics endpoint that needs an extra query
# param folds it into its own subclass of `EmployeeFilterParams` instead of
# declaring it as a second parameter.


class DistributionParams(EmployeeFilterParams):
    buckets: int = Field(default=12, ge=5, le=30)


class ByDimensionParams(EmployeeFilterParams):
    dimension: Literal["department", "country", "job_role", "level"]


class PayEquityParams(EmployeeFilterParams):
    dimension: Literal["gender"] = "gender"
    group_by: Literal["job_role_level"] = "job_role_level"
    min_sample_size: int = Field(default=5, ge=1, le=1000)
