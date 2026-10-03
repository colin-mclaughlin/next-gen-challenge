from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.holding import Holding


class Security(Base):
    """Security master: one row per ticker, shared by every portfolio that holds it.

    Price lives here (not on the holding) because a price is a fact about the security:
    AAPL is held in two portfolios but has one price.
    """

    __tablename__ = "securities"
    __table_args__ = (
        CheckConstraint("dividend_yield IS NULL OR dividend_yield >= 0", name="dividend_yield_non_negative"),
        CheckConstraint("price >= 0", name="price_non_negative"),
        CheckConstraint("previous_close_price >= 0", name="previous_close_non_negative"),
    )

    ticker: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str]
    asset_class: Mapped[str]
    sector: Mapped[str | None]
    dividend_yield: Mapped[float | None]  # None = pays no dividend (distinct from 0%)
    fifty_two_week_low: Mapped[float | None]
    fifty_two_week_high: Mapped[float | None]
    price: Mapped[float]
    previous_close_price: Mapped[float]

    holdings: Mapped[list[Holding]] = relationship(back_populates="security")
    price_history: Mapped[list[PricePoint]] = relationship(back_populates="security", order_by="PricePoint.date")


class PricePoint(Base):
    """A security's price on one date."""

    __tablename__ = "security_price_history"
    __table_args__ = (CheckConstraint("price >= 0", name="price_non_negative"),)

    ticker: Mapped[str] = mapped_column(ForeignKey("securities.ticker"), primary_key=True)
    date: Mapped[datetime.date] = mapped_column(primary_key=True)
    price: Mapped[float]

    security: Mapped[Security] = relationship(back_populates="price_history")
