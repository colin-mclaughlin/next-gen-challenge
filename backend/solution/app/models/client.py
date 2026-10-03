from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.portfolio import Portfolio


class Client(Base):
    """A person/household who owns one or more portfolios."""

    __tablename__ = "clients"

    client_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str]

    portfolios: Mapped[list[Portfolio]] = relationship(back_populates="client", order_by="Portfolio.portfolio_id")
