from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.holding import Holding
    from app.models.performance import PerformanceSnapshot


class Portfolio(Base):
    """An account belonging to a client (e.g. "Taxable Brokerage"). Money is in `currency`."""

    __tablename__ = "portfolios"
    __table_args__ = (CheckConstraint("length(currency) = 3", name="currency_iso_code"),)

    portfolio_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.client_id"), index=True)
    label: Mapped[str]
    currency: Mapped[str] = mapped_column(String(3))

    client: Mapped[Client] = relationship(back_populates="portfolios")
    holdings: Mapped[list[Holding]] = relationship(back_populates="portfolio", order_by="Holding.holding_id")
    snapshots: Mapped[list[PerformanceSnapshot]] = relationship(
        back_populates="portfolio", order_by="PerformanceSnapshot.date"
    )
