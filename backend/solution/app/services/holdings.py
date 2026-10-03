"""Task 2: load a portfolio's positions, value them, and shape the API response."""
from sqlalchemy.orm import Session, sessionmaker

from app.db import repositories
from app.domain.holdings import HoldingValuation, value_holdings
from app.domain.rounding import RATIO_PLACES, round_money, round_ratio, round_to
from app.errors import ApiError
from app.schemas import Holding


class HoldingsService:
    def __init__(self, sessions: sessionmaker[Session]):
        self.sessions = sessions

    def valuations(self, portfolio_id: str) -> list[HoldingValuation]:
        """Unrounded valuations, for reuse by aggregate views (allocation, household)."""
        # One short-lived session per call: opened here, closed automatically at the end.
        with self.sessions() as session:
            if not repositories.portfolio_exists(session, portfolio_id):
                raise ApiError(404, "portfolio_not_found", f"Portfolio {portfolio_id} was not found.")
            positions = repositories.list_positions(session, portfolio_id)
        return value_holdings(positions)

    def list_holdings(self, portfolio_id: str) -> list[Holding]:
        return [_to_response(v) for v in self.valuations(portfolio_id)]


def _to_response(v: HoldingValuation) -> Holding:
    p = v.position
    return Holding(
        ticker=p.ticker,
        name=p.name,
        asset_class=p.asset_class,
        quantity=p.quantity,
        cost_basis_per_share=p.cost_basis_per_share,
        price=p.price,
        previous_close_price=p.previous_close_price,
        market_value=round_money(v.market_value),
        weight_percent=round_to(v.weight_percent, RATIO_PLACES),
        unrealized_gain_loss=round_money(v.unrealized_gain_loss),
        day_change_amount=round_money(v.day_change_amount),
        day_change_percent=round_ratio(v.day_change_percent),
    )
