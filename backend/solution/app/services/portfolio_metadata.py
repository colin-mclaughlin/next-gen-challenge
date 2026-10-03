"""Task 1: fetch portfolio metadata from the CRM, map it, and translate failures into API errors.

Task 9 will add the cache / stale-fallback layer here.
"""
from app.errors import ApiError
from app.schemas import PortfolioMetadata
from app.services.crm_client import CrmClient, CrmError
from app.services.crm_mapper import map_crm_portfolio


class PortfolioMetadataService:
    def __init__(self, crm: CrmClient):
        self.crm = crm

    async def get(self, portfolio_id: str) -> PortfolioMetadata:
        try:
            payload = await self.crm.get_portfolio(portfolio_id)
            metadata = map_crm_portfolio(payload, portfolio_id)
        except CrmError as exc:
            raise _to_api_error(exc, portfolio_id) from exc
        if metadata is None:
            raise _to_api_error(CrmError("not_found", "Account not in CRM payload."), portfolio_id)
        return metadata


def _to_api_error(exc: CrmError, portfolio_id: str) -> ApiError:
    if exc.kind == "not_found":
        return ApiError(404, "portfolio_not_found", f"Portfolio {portfolio_id} was not found.")
    if exc.kind == "timeout":
        return ApiError(504, "crm_timeout", "The CRM did not respond in time. Please try again shortly.")
    if exc.kind == "unavailable":
        return ApiError(502, "crm_unavailable", "The CRM is temporarily unavailable. Please try again shortly.")
    return ApiError(502, "bad_crm_response", "The CRM returned data that could not be read.")
