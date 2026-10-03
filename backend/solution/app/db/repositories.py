"""SQL access only: queries that return plain domain objects. No calculations here."""
import sqlite3

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
