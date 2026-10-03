"""HTTP client for the legacy CRM.

Returns the raw CRM payload or raises CrmError, whose `kind` tells callers how the call failed
(used for HTTP error mapping, and by any future cache to decide when to serve a stale fallback).
"""
import asyncio
from typing import Any, Literal
from urllib.parse import quote

import httpx

CrmErrorKind = Literal["not_found", "timeout", "unavailable", "bad_response"]


class CrmError(Exception):
    def __init__(self, kind: CrmErrorKind, message: str):
        super().__init__(message)
        self.kind = kind


class CrmClient:
    def __init__(self, base_url: str, timeout_seconds: float = 2.0, transport: httpx.AsyncBaseTransport | None = None):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._transport = transport  # injectable for tests (httpx.MockTransport)
        self._client: httpx.AsyncClient | None = None

    def _http(self) -> httpx.AsyncClient:
        # One shared client: reuses connections, and its (slow-to-build) SSL context is created
        # once, outside the timed section, so it can't eat into the CRM time budget.
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout_seconds, transport=self._transport)
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get_portfolio(self, portfolio_id: str) -> Any:
        """Fetch the raw CRM record containing the given portfolio (account) id."""
        url = f"{self.base_url}/crm/portfolios/{quote(portfolio_id, safe='')}"
        client = self._http()
        try:
            # httpx timeouts are per network operation; asyncio.timeout caps the whole call
            # (connect + headers + body) so a slow-dripping CRM can't hang the request either.
            async with asyncio.timeout(self.timeout_seconds):
                response = await client.get(url, headers={"Accept": "application/json"})
        except (TimeoutError, httpx.TimeoutException):
            raise CrmError("timeout", f"CRM did not respond within {self.timeout_seconds}s.") from None
        except httpx.HTTPError as exc:
            raise CrmError("unavailable", f"Could not reach the CRM: {exc}") from exc

        status = response.status_code
        if status == 404:
            raise CrmError("not_found", f"CRM has no account {portfolio_id}.")
        if status in (408, 504):
            raise CrmError("timeout", f"CRM reported a timeout (HTTP {status}).")
        if status >= 500:
            raise CrmError("unavailable", f"CRM returned HTTP {status}.")
        if not response.is_success:
            raise CrmError("bad_response", f"CRM returned unexpected HTTP {status}.")

        try:
            return response.json()
        except ValueError:
            raise CrmError("bad_response", "CRM returned a body that is not valid JSON.") from None
