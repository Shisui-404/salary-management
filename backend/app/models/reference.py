"""Small reference/lookup tables: Department, JobRole, Level, Country.

Kept as real FK-backed tables (not free-text columns) so filters and
group-bys in the analytics queries are index-backed joins rather than string
matching, and so the `/reference` endpoint has one obvious source per facet.
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    employees: Mapped[list["Employee"]] = relationship(back_populates="department")


class JobRole(Base):
    __tablename__ = "job_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    employees: Mapped[list["Employee"]] = relationship(back_populates="job_role")


class Level(Base):
    __tablename__ = "levels"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    rank: Mapped[int] = mapped_column(nullable=False)

    employees: Mapped[list["Employee"]] = relationship(back_populates="level")


class Country(Base):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(2), unique=True, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    employees: Mapped[list["Employee"]] = relationship(back_populates="country")
