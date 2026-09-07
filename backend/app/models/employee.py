"""The Employee model.

Employees hold job/personal attributes only. Compensation lives entirely in
`SalaryRecord` (see `salary_record.py`) — there is deliberately no
`salary`/`amount` column here, so it is structurally impossible to overwrite
a salary in place.
"""

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.db.session import Base
from app.models.enums import EmploymentStatus, Gender

if TYPE_CHECKING:
    from app.models.reference import Country, Department, JobRole, Level
    from app.models.salary_record import SalaryRecord


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = (UniqueConstraint("employee_code", name="uq_employees_employee_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    gender: Mapped[Gender] = mapped_column(
        Enum(Gender, native_enum=False, length=20), nullable=False
    )
    hire_date: Mapped[dt.date] = mapped_column(nullable=False)
    employment_status: Mapped[EmploymentStatus] = mapped_column(
        Enum(EmploymentStatus, native_enum=False, length=20),
        nullable=False,
        default=EmploymentStatus.ACTIVE,
    )

    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False)
    job_role_id: Mapped[int] = mapped_column(ForeignKey("job_roles.id"), nullable=False)
    level_id: Mapped[int] = mapped_column(ForeignKey("levels.id"), nullable=False)
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"), nullable=False)
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)

    department: Mapped["Department"] = relationship(back_populates="employees")
    job_role: Mapped["JobRole"] = relationship(back_populates="employees")
    level: Mapped["Level"] = relationship(back_populates="employees")
    country: Mapped["Country"] = relationship(back_populates="employees")
    manager: Mapped["Employee | None"] = relationship(remote_side=[id])

    salary_records: Mapped[list["SalaryRecord"]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="SalaryRecord.effective_from.desc()",
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
