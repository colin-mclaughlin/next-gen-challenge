import asyncio
import time

import httpx
import pytest

from app.services.crm_client import CrmClient, CrmError


def client_with(handler, timeout_seconds=0.05) -> CrmClient:
    return CrmClient("http://crm.test/", timeout_seconds, transport=httpx.MockTransport(handler))


def fetch(client: CrmClient, portfolio_id="x"):
    async def exercise():
        try:
            return await client.get_portfolio(portfolio_id)
        finally:
            await client.aclose()

    return asyncio.run(exercise())


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


def test_requests_json_using_get():
    def handler(request):
        assert request.method == "GET"
        assert request.headers["accept"] == "application/json"
        return httpx.Response(200, json={"client_record": {}})

    assert fetch(client_with(handler)) == {"client_record": {}}


def test_http_408_is_classified_as_timeout():
    assert error_kind(client_with(lambda _: httpx.Response(408))) == "timeout"


@pytest.mark.parametrize("exception", [httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout])
def test_httpx_timeout_exceptions_are_classified_as_timeout(exception):
    def handler(request):
        raise exception("operation timed out", request=request)

    assert error_kind(client_with(handler)) == "timeout"


def test_total_timeout_covers_response_body_and_cancels_the_read():
    class HangingBody(httpx.AsyncByteStream):
        def __init__(self):
            self.cancelled = False

        async def __aiter__(self):
            yield b'{"client_record":'
            try:
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                self.cancelled = True
                raise
            yield b'{}}'

    body = HangingBody()
    client = client_with(lambda _: httpx.Response(200, stream=body))
    started = time.monotonic()

    assert error_kind(client) == "timeout"
    assert body.cancelled, "the stalled body read must not keep running after the request times out"
    assert time.monotonic() - started < 1


def test_same_client_can_recover_after_network_failure():
    attempts = []

    def handler(request):
        attempts.append(request)
        if len(attempts) == 1:
            raise httpx.ConnectError("connection refused", request=request)
        return httpx.Response(200, json={"ok": True})

    client = client_with(handler)

    async def exercise():
        try:
            with pytest.raises(CrmError) as caught:
                await client.get_portfolio("P-9001")
            assert caught.value.kind == "unavailable"
            return await client.get_portfolio("P-9001")
        finally:
            await client.aclose()

    assert asyncio.run(exercise()) == {"ok": True}
    assert len(attempts) == 2
