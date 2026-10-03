from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.portfolio import Portfolio


class PerformanceSnapshot(Base):
    """A portfolio's total market value on one date (for the performance chart)."""

    __tablename__ = "performance_snapshots"
    __table_args__ = (CheckConstraint("market_value >= 0", name="market_value_non_negative"),)

    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.portfolio_id"), primary_key=True)
    date: Mapped[datetime.date] = mapped_column(primary_key=True)
    market_value: Mapped[float]

    portfolio: Mapped[Portfolio] = relationship(back_populates="snapshots")
