"""SalaryBand: min/mid/max compensation band for a (job_role, level, country).

Amounts are stored the same way as `SalaryRecord` — integer minor units plus
an ISO-4217 currency — and normalised to `BASE_CURRENCY` on read for
compa-ratio / band-position comparisons, exactly like salaries.
"""

from sqlalchemy import BigInteger, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SalaryBand(Base):
    __tablename__ = "salary_bands"
    __table_args__ = (
        UniqueConstraint(
            "job_role_id", "level_id", "country_id", name="uq_salary_bands_role_level_country"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    job_role_id: Mapped[int] = mapped_column(ForeignKey("job_roles.id"), nullable=False)
    level_id: Mapped[int] = mapped_column(ForeignKey("levels.id"), nullable=False)
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"), nullable=False)

    min_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mid_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    max_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
