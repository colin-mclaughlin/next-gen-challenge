from __future__ import annotations

import enum
import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.holding import Holding


class TransactionType(enum.StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class Transaction(Base):
    """One BUY or SELL in a holding's ledger."""

    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("price >= 0", name="price_non_negative"),
        Index(None, "holding_id", "date"),
    )

    transaction_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    holding_id: Mapped[str] = mapped_column(ForeignKey("holdings.holding_id"))
    # Stored as the text 'BUY'/'SELL' with a CHECK constraint; Python sees a TransactionType.
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, native_enum=False, create_constraint=True, name="transaction_type", length=4)
    )
    quantity: Mapped[float]
    price: Mapped[float]
    date: Mapped[datetime.date]

    holding: Mapped[Holding] = relationship(back_populates="transactions")
