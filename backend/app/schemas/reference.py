"""Lookup/reference DTOs — `RefItem` and the `/reference` aggregate response."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.models.enums import ChangeReason, EmploymentStatus, Gender


class RefItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class LevelRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    rank: int


class CountryRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    currency: str


class ReferenceResponse(BaseModel):
    departments: list[RefItem]
    job_roles: list[RefItem]
    levels: list[LevelRef]
    countries: list[CountryRef]
    genders: list[Gender]
    employment_statuses: list[EmploymentStatus]
    change_reasons: list[ChangeReason]
    base_currency: str
