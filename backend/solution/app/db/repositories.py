"""Repositories: the only code that queries the database.

Each function takes a Session (one unit of work) and returns plain domain objects, so services
and calculations never see SQL or ORM details. Queries are built with SQLAlchemy (always
parameterised) against the models in app/models.
"""
import datetime

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.domain.history import Snapshot
from app.domain.holdings import Position
from app.models import Holding, PerformanceSnapshot, Portfolio, Security


def portfolio_exists(session: Session, portfolio_id: str) -> bool:
    return bool(session.scalar(select(exists().where(Portfolio.portfolio_id == portfolio_id))))


def list_positions(session: Session, portfolio_id: str) -> list[Position]:
    """A portfolio's holdings joined to their security (name, asset class, prices)."""
    rows = session.execute(
        select(Holding, Security)
        .join(Holding.security)
        .where(Holding.portfolio_id == portfolio_id)
        .order_by(Holding.holding_id)
    )
    return [
        Position(
            ticker=holding.ticker,
            name=security.name,
            asset_class=security.asset_class,
            quantity=holding.quantity,
            cost_basis_per_share=holding.cost_basis_per_share,
            price=security.price,
            previous_close_price=security.previous_close_price,
        )
        for holding, security in rows
    ]


def list_snapshots(
    session: Session, portfolio_id: str, start: datetime.date | None, end: datetime.date
) -> list[Snapshot]:
    """Snapshots with start <= date <= end (no lower bound when start is None), oldest first."""
    query = select(PerformanceSnapshot).where(
        PerformanceSnapshot.portfolio_id == portfolio_id, PerformanceSnapshot.date <= end
    )
    if start is not None:
        query = query.where(PerformanceSnapshot.date >= start)
    snapshots = session.scalars(query.order_by(PerformanceSnapshot.date))
    return [Snapshot(date=s.date.isoformat(), market_value=s.market_value) for s in snapshots]
