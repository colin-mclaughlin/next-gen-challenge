from fastapi import APIRouter, Request

from app.errors import ErrorResponse
from app.schemas import Holding
from app.services.holdings import HoldingsService

router = APIRouter(prefix="/portfolios", tags=["holdings"])


def _holdings_service(request: Request) -> HoldingsService:
    service: HoldingsService = request.app.state.holdings
    return service


@router.get("/{portfolio_id}/holdings", response_model=list[Holding], responses={404: {"model": ErrorResponse}})
async def get_holdings(portfolio_id: str, request: Request) -> list[Holding]:
    # async on purpose: keeps all SQLite access on the event-loop thread (see docs/task-02.md).
    return _holdings_service(request).list_holdings(portfolio_id)
