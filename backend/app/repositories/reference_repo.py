"""Lookup-table queries backing `/reference` and FK-existence checks on create/update."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.reference import Country, Department, JobRole, Level


def list_departments(db: Session) -> list[Department]:
    return list(db.execute(select(Department).order_by(Department.name)).scalars().all())


def list_job_roles(db: Session) -> list[JobRole]:
    return list(db.execute(select(JobRole).order_by(JobRole.name)).scalars().all())


def list_levels(db: Session) -> list[Level]:
    return list(db.execute(select(Level).order_by(Level.rank)).scalars().all())


def list_countries(db: Session) -> list[Country]:
    return list(db.execute(select(Country).order_by(Country.name)).scalars().all())


def department_exists(db: Session, department_id: int) -> bool:
    return db.get(Department, department_id) is not None


def job_role_exists(db: Session, job_role_id: int) -> bool:
    return db.get(JobRole, job_role_id) is not None


def level_exists(db: Session, level_id: int) -> bool:
    return db.get(Level, level_id) is not None


def country_exists(db: Session, country_id: int) -> bool:
    return db.get(Country, country_id) is not None


def get_department_by_name(db: Session, name: str) -> Department | None:
    return db.execute(select(Department).where(Department.name == name)).scalar_one_or_none()


def get_job_role_by_name(db: Session, name: str) -> JobRole | None:
    return db.execute(select(JobRole).where(JobRole.name == name)).scalar_one_or_none()


def get_level_by_name(db: Session, name: str) -> Level | None:
    return db.execute(select(Level).where(Level.name == name)).scalar_one_or_none()


def get_country_by_name(db: Session, name: str) -> Country | None:
    return db.execute(select(Country).where(Country.name == name)).scalar_one_or_none()
