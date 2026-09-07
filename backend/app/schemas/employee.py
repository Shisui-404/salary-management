"""Employee request/response DTOs — matches `docs/api-contract.md` exactly.

`current_salary`, `compa_ratio`, `band_position` and `band` are all derived
(never stored columns on `Employee`), so `EmployeeOut` is always built
explicitly by `services/salary_service.py` from a repository row plus the
computed compensation-intelligence fields — never via a bare
`model_validate` on the ORM object.
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import BandPosition, ChangeReason, EmploymentStatus, Gender
from app.schemas.reference import CountryRef, LevelRef, RefItem


class BandInfo(BaseModel):
    min: str
    mid: str
    max: str
    currency: str


class CurrentSalary(BaseModel):
    amount: str
    currency: str
    amount_base: str
    base_currency: str
    effective_from: dt.date
    change_reason: ChangeReason


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_code: str
    first_name: str
    last_name: str
    full_name: str
    email: str
    gender: Gender
    hire_date: dt.date
    employment_status: EmploymentStatus
    department: RefItem
    job_role: RefItem
    level: LevelRef
    country: CountryRef
    manager_id: int | None
    current_salary: CurrentSalary | None
    compa_ratio: float | None
    band_position: BandPosition
    band: BandInfo | None


class InitialSalaryIn(BaseModel):
    amount: str
    currency: str = Field(min_length=3, max_length=3)


class EmployeeCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    gender: Gender
    hire_date: dt.date
    department_id: int
    job_role_id: int
    level_id: int
    country_id: int
    manager_id: int | None = None
    employment_status: EmploymentStatus = EmploymentStatus.ACTIVE
    initial_salary: InitialSalaryIn | None = None


class EmployeeUpdate(BaseModel):
    """Any subset of the non-salary employee fields. Salary is never changed here —
    see `POST /employees/{id}/salary` instead."""

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    gender: Gender | None = None
    hire_date: dt.date | None = None
    department_id: int | None = None
    job_role_id: int | None = None
    level_id: int | None = None
    country_id: int | None = None
    manager_id: int | None = None
    employment_status: EmploymentStatus | None = None
