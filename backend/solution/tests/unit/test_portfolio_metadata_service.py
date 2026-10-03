"""Task 1 orchestration tests, using an injected CRM instead of a network server."""
import asyncio
from unittest.mock import AsyncMock

import pytest

from app.errors import ApiError
from app.services.crm_client import CrmError
from app.services.portfolio_metadata import PortfolioMetadataService


def crm_payload():
    return {
        "client_record": {
            "client_id": "abc123",
            "accounts": [{
                "acct_ref": "P-9001",
                "acct_nickname": "Taxable Brokerage",
                "curr_val": {"amt": 100, "ccy": "CAD"},
                "chg_1d": {"amt": -1, "pct": -0.01},
                "since_inception_pct": 0.187,
            }],
        },
        "meta": {"retrieved_at": "2025-06-01T10:00:00Z"},
    }


def test_fetches_requested_portfolio_from_crm_and_returns_mapped_metadata():
    crm = AsyncMock()
    crm.get_portfolio.return_value = crm_payload()

    result = asyncio.run(PortfolioMetadataService(crm).get("P-9001"))

    crm.get_portfolio.assert_awaited_once_with("P-9001")
    assert result.model_dump(by_alias=True) == {
        "portfolioId": "P-9001", "clientId": "abc123",
        "label": "Taxable Brokerage", "currency": "CAD",
        "totalMarketValue": 100, "dayChangeAmount": -1,
        "dayChangePercent": -0.01, "totalReturnSinceInception": 0.187,
        "asOf": "2025-06-01T10:00:00.000Z",
    }


@pytest.mark.parametrize(
    ("kind", "status", "code", "message"),
    [
        ("not_found", 404, "portfolio_not_found", "Portfolio P-9001 was not found."),
        ("timeout", 504, "crm_timeout", "The CRM did not respond in time. Please try again shortly."),
        ("unavailable", 502, "crm_unavailable", "The CRM is temporarily unavailable. Please try again shortly."),
        ("bad_response", 502, "bad_crm_response", "The CRM returned data that could not be read."),
    ],
)
def test_translates_crm_failures_into_public_errors(kind, status, code, message):
    crm = AsyncMock()
    crm.get_portfolio.side_effect = CrmError(kind, "internal upstream diagnostic")

    with pytest.raises(ApiError) as caught:
        asyncio.run(PortfolioMetadataService(crm).get("P-9001"))

    assert caught.value.status_code == status
    assert caught.value.code == code
    assert caught.value.message == message
    crm.get_portfolio.assert_awaited_once_with("P-9001")


def test_successful_crm_response_without_requested_account_is_not_found():
    crm = AsyncMock()
    crm.get_portfolio.return_value = crm_payload()

    with pytest.raises(ApiError) as caught:
        asyncio.run(PortfolioMetadataService(crm).get("UNKNOWN"))

    assert caught.value.status_code == 404
    assert caught.value.code == "portfolio_not_found"
    assert caught.value.message == "Portfolio UNKNOWN was not found."


@pytest.mark.parametrize("raw", [None, {}, {"client_record": {"accounts": [{"acct_ref": "P-9001"}]}}])
def test_unusable_crm_payload_is_bad_gateway_instead_of_internal_error(raw):
    crm = AsyncMock()
    crm.get_portfolio.return_value = raw
    with pytest.raises(ApiError) as caught:
        asyncio.run(PortfolioMetadataService(crm).get("P-9001"))

    assert caught.value.status_code == 502
    assert caught.value.code == "bad_crm_response"


def test_successful_request_after_failure_returns_fresh_crm_metadata():
    crm = AsyncMock()
    crm.get_portfolio.side_effect = [CrmError("unavailable", "outage"), crm_payload()]
    service = PortfolioMetadataService(crm)

    async def exercise():
        with pytest.raises(ApiError):
            await service.get("P-9001")
        return await service.get("P-9001")

    assert asyncio.run(exercise()).total_market_value == 100
    assert crm.get_portfolio.await_count == 2
