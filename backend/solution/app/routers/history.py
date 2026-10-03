from fastapi import APIRouter, Query, Request

from app.domain.history import RANGES
from app.errors import ErrorResponse
from app.schemas import PerformancePoint
from app.services.history import HistoryService

router = APIRouter(prefix="/portfolios", tags=["performance"])


def _history_service(request: Request) -> HistoryService:
    service: HistoryService = request.app.state.history
    return service


@router.get(
    "/{portfolio_id}/performance-history",
    response_model=list[PerformancePoint],
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def get_performance_history(
    portfolio_id: str,
    request: Request,
    # A plain string (not an enum) so invalid values get our own `invalid_range` 400, not a generic error.
    range_: str | None = Query(
        None, alias="range", description=f"One of {', '.join(RANGES)}. Defaults to All.", examples=list(RANGES)
    ),
) -> list[PerformancePoint]:
    return _history_service(request).get(portfolio_id, range_)
