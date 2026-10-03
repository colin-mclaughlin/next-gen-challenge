from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.portfolio import Portfolio
    from app.models.security import Security
    from app.models.transaction import Transaction


class Holding(Base):
    """A portfolio's position in one security.

    `quantity` and `cost_basis_per_share` are stored snapshots from the seed data. A later
    ledger-replay feature could derive them from `transactions` instead.
    """

    __tablename__ = "holdings"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "ticker"),  # one position per security per portfolio
        CheckConstraint("quantity >= 0", name="quantity_non_negative"),
        CheckConstraint("cost_basis_per_share >= 0", name="cost_basis_non_negative"),
    )

    holding_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.portfolio_id"))
    ticker: Mapped[str] = mapped_column(ForeignKey("securities.ticker"))
    quantity: Mapped[float]
    cost_basis_per_share: Mapped[float]

    portfolio: Mapped[Portfolio] = relationship(back_populates="holdings")
    security: Mapped[Security] = relationship(back_populates="holdings")
    transactions: Mapped[list[Transaction]] = relationship(
        back_populates="holding", order_by="Transaction.date"
    )
