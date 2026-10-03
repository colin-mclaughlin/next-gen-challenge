"""End-to-end tests for GET /portfolios/{id} against the real mock CRM."""
import re
import time

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

CRM_TIMEOUT_SECONDS = 0.5


@pytest.fixture
def client(mock_crm, engine):
    app = create_app(Settings(crm_base_url=mock_crm.base_url, crm_timeout_seconds=CRM_TIMEOUT_SECONDS), engine=engine)
    with TestClient(app) as test_client:
        yield test_client


def test_maps_successful_crm_response(client, mock_crm):
    mock_crm.set_mode("ok")
    res = client.get("/portfolios/P-9001")
    assert res.status_code == 200
    body = res.json()
    assert body["portfolioId"] == "P-9001"
    assert body["clientId"] == "abc123"
    assert body["label"] == "Taxable Brokerage"
    assert body["currency"] == "CAD"
    assert body["totalMarketValue"] == 48930
    assert body["dayChangeAmount"] == 30
    assert body["dayChangePercent"] == pytest.approx(30 / 48900)
    assert body["totalReturnSinceInception"] == 0.187
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", body["asOf"])
    assert len(body) == 9, "no raw CRM fields leak through"


def test_selects_requested_account_when_not_first(client, mock_crm):
    mock_crm.set_mode("ok")
    body = client.get("/portfolios/P-9002").json()
    assert body["portfolioId"] == "P-9002"
    assert body["label"] == "Retirement Account"
    assert body["totalMarketValue"] == 500


def test_unknown_id_returns_structured_404(client, mock_crm):
    mock_crm.set_mode("ok")
    res = client.get("/portfolios/UNKNOWN")
    assert res.status_code == 404
    assert res.json() == {"error": "portfolio_not_found", "message": "Portfolio UNKNOWN was not found."}


def test_crm_error_returns_502(client, mock_crm):
    mock_crm.set_mode("error")
    res = client.get("/portfolios/P-9001")
    assert res.status_code == 502
    assert res.json()["error"] == "crm_unavailable"


def test_crm_timeout_returns_504_promptly(client, mock_crm):
    mock_crm.set_mode("timeout")
    started = time.monotonic()
    res = client.get("/portfolios/P-9001")
    elapsed = time.monotonic() - started
    assert res.status_code == 504
    assert res.json()["error"] == "crm_timeout"
    assert elapsed < CRM_TIMEOUT_SECONDS + 1, f"took {elapsed:.2f}s; should not wait for the CRM's 10s"


def test_missing_crm_fields_map_to_null(client, mock_crm):
    mock_crm.set_mode("missing")
    res = client.get("/portfolios/P-9001")
    assert res.status_code == 200
    body = res.json()
    assert body["label"] is None
    assert body["totalMarketValue"] is None
    assert body["dayChangeAmount"] == 30


def test_accounts_nested_under_relationships(client, mock_crm):
    mock_crm.set_mode("nested")
    res = client.get("/portfolios/P-9002")
    assert res.status_code == 200
    assert res.json()["portfolioId"] == "P-9002"


def test_survives_default_auto_failure_pattern(client, mock_crm):
    mock_crm.set_mode("auto")
    statuses = [client.get("/portfolios/P-9001").status_code for _ in range(10)]
    assert set(statuses) <= {200, 502, 504}, statuses
    assert 200 in statuses


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_unknown_route_returns_structured_404(client):
    res = client.get("/nope")
    assert res.status_code == 404
    assert res.json()["error"] == "not_found"


def test_wrong_method_returns_structured_405(client):
    res = client.post("/portfolios/P-9001")
    assert res.status_code == 405
    assert res.json()["error"] == "method_not_allowed"
