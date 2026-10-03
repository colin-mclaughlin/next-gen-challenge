"""SQL access only: queries that return plain domain objects. No calculations here."""
import sqlite3
from datetime import date

from app.domain.history import Snapshot
from app.domain.holdings import Position


def portfolio_exists(conn: sqlite3.Connection, portfolio_id: str) -> bool:
    row = conn.execute("SELECT 1 FROM portfolios WHERE portfolio_id = ?", (portfolio_id,)).fetchone()
    return row is not None


def list_positions(conn: sqlite3.Connection, portfolio_id: str) -> list[Position]:
    rows = conn.execute(
        """
        SELECT h.ticker, s.name, s.asset_class, h.quantity, h.cost_basis_per_share,
               s.price, s.previous_close_price
        FROM holdings h
        JOIN securities s ON s.ticker = h.ticker
        WHERE h.portfolio_id = ?
        ORDER BY h.holding_id
        """,
        (portfolio_id,),
    ).fetchall()
    return [
        Position(
            ticker=row["ticker"],
            name=row["name"],
            asset_class=row["asset_class"],
            quantity=row["quantity"],
            cost_basis_per_share=row["cost_basis_per_share"],
            price=row["price"],
            previous_close_price=row["previous_close_price"],
        )
        for row in rows
    ]


def list_snapshots(conn: sqlite3.Connection, portfolio_id: str, start: date | None, end: date) -> list[Snapshot]:
    """Snapshots with start <= date <= end (no lower bound when start is None), oldest first."""
    start_iso = start.isoformat() if start else None
    rows = conn.execute(
        """
        SELECT date, market_value FROM performance_snapshots
        WHERE portfolio_id = :portfolio_id
          AND (:start IS NULL OR date >= :start)
          AND date <= :end
        ORDER BY date
        """,
        {"portfolio_id": portfolio_id, "start": start_iso, "end": end.isoformat()},
    ).fetchall()
    return [Snapshot(date=row["date"], market_value=row["market_value"]) for row in rows]
