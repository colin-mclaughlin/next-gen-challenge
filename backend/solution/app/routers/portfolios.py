from fastapi import APIRouter, Request

from app.errors import ErrorResponse
from app.schemas import PortfolioMetadata
from app.services.portfolio_metadata import PortfolioMetadataService

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


def _metadata_service(request: Request) -> PortfolioMetadataService:
    service: PortfolioMetadataService = request.app.state.portfolio_metadata
    return service


@router.get(
    "/{portfolio_id}",
    response_model=PortfolioMetadata,
    responses={404: {"model": ErrorResponse}, 502: {"model": ErrorResponse}, 504: {"model": ErrorResponse}},
)
async def get_portfolio(portfolio_id: str, request: Request) -> PortfolioMetadata:
    return await _metadata_service(request).get(portfolio_id)
