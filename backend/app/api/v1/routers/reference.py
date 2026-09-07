"""`GET /reference` — all lookup data for filter dropdowns in one call."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.db.session import DbSession
from app.models.enums import ChangeReason, EmploymentStatus, Gender
from app.repositories import reference_repo
from app.schemas.reference import ReferenceResponse

router = APIRouter(tags=["reference"])


@router.get("/reference", response_model=ReferenceResponse)
def get_reference(db: DbSession) -> ReferenceResponse:
    return ReferenceResponse(
        departments=reference_repo.list_departments(db),
        job_roles=reference_repo.list_job_roles(db),
        levels=reference_repo.list_levels(db),
        countries=reference_repo.list_countries(db),
        genders=list(Gender),
        employment_statuses=list(EmploymentStatus),
        change_reasons=list(ChangeReason),
        base_currency=get_settings().base_currency,
    )
