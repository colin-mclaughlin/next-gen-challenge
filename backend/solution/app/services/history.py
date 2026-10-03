"""Task 3: performance history filtered to a date range ending today."""
from sqlalchemy.orm import Session, sessionmaker

from app.clock import Clock, utc_today
from app.db import repositories
from app.domain.history import InvalidRange, parse_range, range_start
from app.domain.rounding import round_money
from app.errors import ApiError
from app.schemas import PerformancePoint


class HistoryService:
    def __init__(self, sessions: sessionmaker[Session], clock: Clock = utc_today):
        self.sessions = sessions
        self.clock = clock

    def get(self, portfolio_id: str, raw_range: str | None) -> list[PerformancePoint]:
        # Validate input before looking anything up: a bad request is a 400 regardless of the id.
        try:
            range_ = parse_range(raw_range)
        except InvalidRange as exc:
            raise ApiError(400, "invalid_range", str(exc)) from exc

        today = self.clock()
        with self.sessions() as session:  # one short-lived session per call
            if not repositories.portfolio_exists(session, portfolio_id):
                raise ApiError(404, "portfolio_not_found", f"Portfolio {portfolio_id} was not found.")
            snapshots = repositories.list_snapshots(session, portfolio_id, range_start(range_, today), today)
        return [PerformancePoint(date=s.date, market_value=round_money(s.market_value)) for s in snapshots]
