import asyncio
import time

import httpx
import pytest

from app.services.crm_client import CrmClient, CrmError


def client_with(handler, timeout_seconds=0.05) -> CrmClient:
    return CrmClient("http://crm.test/", timeout_seconds, transport=httpx.MockTransport(handler))


def fetch(client: CrmClient, portfolio_id="x"):
    return asyncio.run(client.get_portfolio(portfolio_id))


def error_kind(client: CrmClient) -> str:
    with pytest.raises(CrmError) as info:
        fetch(client)
    return info.value.kind


def test_requests_encoded_url_and_returns_parsed_body():
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"ok": True})

    assert fetch(client_with(handler), "P 1/2") == {"ok": True}
    assert seen["url"] == "http://crm.test/crm/portfolios/P%201%2F2"


@pytest.mark.parametrize(
    ("status", "kind"),
    [(404, "not_found"), (503, "unavailable"), (500, "unavailable"), (504, "timeout"), (400, "bad_response")],
)
def test_classifies_http_failures(status, kind):
    assert error_kind(client_with(lambda _: httpx.Response(status, json={}))) == kind


def test_aborts_with_timeout_when_crm_hangs():
    async def hanging(_):
        await asyncio.sleep(5)
        return httpx.Response(200, json={})

    started = time.monotonic()
    assert error_kind(client_with(hanging, timeout_seconds=0.05)) == "timeout"
    assert time.monotonic() - started < 1, "should not wait for the CRM"


def test_network_error_is_unavailable():
    def refuse(request):
        raise httpx.ConnectError("connection refused", request=request)

    assert error_kind(client_with(refuse)) == "unavailable"


def test_invalid_json_is_bad_response():
    assert error_kind(client_with(lambda _: httpx.Response(200, text="<html>"))) == "bad_response"
