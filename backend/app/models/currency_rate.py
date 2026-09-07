"""CurrencyRate: static, dated exchange rates to `BASE_CURRENCY`.

Deliberately not a live feed (see docs/decisions/ADR-003-fx-normalisation.md).
`rate_to_base` is stored as `Numeric` (fixed-point, not float) so
`amount_base = amount * rate_to_base` can be computed exactly and pushed
entirely into SQL — see `services/fx.py`.
"""

import datetime as dt
import decimal

from sqlalchemy import Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class CurrencyRate(Base):
    __tablename__ = "currency_rates"
    __table_args__ = (
        UniqueConstraint("currency", "valid_from", name="uq_currency_rates_currency_from"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    rate_to_base: Mapped[decimal.Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    valid_from: Mapped[dt.date] = mapped_column(nullable=False)
