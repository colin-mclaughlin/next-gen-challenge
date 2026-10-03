from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ExchangeRate(Base):
    """Conversion rate: 1 unit of `base_currency` = `rate` units of `quote_currency`."""

    __tablename__ = "exchange_rates"
    __table_args__ = (CheckConstraint("rate > 0", name="rate_positive"),)

    base_currency: Mapped[str] = mapped_column(String(3), primary_key=True)
    quote_currency: Mapped[str] = mapped_column(String(3), primary_key=True)
    rate: Mapped[float]
