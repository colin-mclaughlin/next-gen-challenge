"""End-to-end tests for GET /portfolios/{id}/holdings (seeded in-memory SQLite)."""
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

FIELDS = {
    "ticker", "name", "assetClass", "quantity", "costBasisPerShare", "price", "previousClosePrice",
    "marketValue", "weightPercent", "unrealizedGainLoss", "dayChangeAmount", "dayChangePercent",
}


def holdings(client, portfolio_id):
    res = client.get(f"/portfolios/{portfolio_id}/holdings")
    return res.status_code, res.json()


def test_p9001_returns_all_holdings_with_calculated_fields(app_client):
    status, body = holdings(app_client, "P-9001")
    assert status == 200
    assert [h["ticker"] for h in body] == ["AAPL", "BND", "ZERO"]
    assert all(set(h) == FIELDS for h in body)

    aapl, bnd, zero = body
    assert aapl == {
        "ticker": "AAPL", "name": "Apple Inc.", "assetClass": "Equity",
        "quantity": 120, "costBasisPerShare": 200, "price": 227.5, "previousClosePrice": 225,
        "marketValue": 27300, "weightPercent": 0.557940, "unrealizedGainLoss": 3300,
        "dayChangeAmount": 300, "dayChangePercent": 0.011111,
    }
    assert (bnd["marketValue"], bnd["unrealizedGainLoss"], bnd["dayChangeAmount"]) == (21630, -570, -270)
    assert bnd["weightPercent"] == 0.44206
    assert bnd["dayChangePercent"] == -0.012329
    assert sum(h["marketValue"] for h in body) == 48930  # matches the CRM's P-9001 total


def test_zero_quantity_holding_has_zero_values(app_client):
    _, body = holdings(app_client, "P-9001")
    zero = next(h for h in body if h["ticker"] == "ZERO")
    assert (zero["marketValue"], zero["weightPercent"], zero["unrealizedGainLoss"], zero["dayChangeAmount"]) == (0, 0, 0, 0)


def test_zero_previous_close_returns_null_percent(app_client):
    status, body = holdings(app_client, "P-9002")
    assert status == 200
    (new,) = body
    assert new["dayChangePercent"] is None
    assert new["dayChangeAmount"] == 500
    assert new["weightPercent"] == 1.0


def test_empty_portfolio_returns_empty_array(app_client):
    assert holdings(app_client, "P-EMPTY") == (200, [])


def test_single_holding_portfolio(app_client):
    _, body = holdings(app_client, "P-SINGLE")
    assert [(h["ticker"], h["weightPercent"], h["marketValue"]) for h in body] == [("AAPL", 1.0, 2275)]


def test_unknown_portfolio_returns_structured_404(app_client):
    assert holdings(app_client, "UNKNOWN") == (
        404,
        {"error": "portfolio_not_found", "message": "Portfolio UNKNOWN was not found."},
    )


def test_trailing_slash_redirects_to_holdings(app_client):
    res = app_client.get("/portfolios/P-9001/holdings/")  # TestClient follows FastAPI's 307 redirect
    assert res.status_code == 200
    assert len(res.json()) == 3


def test_misspelled_sub_route_is_structured_404(app_client):
    res = app_client.get("/portfolios/P-9001/holdingz")
    assert res.status_code == 404
    assert res.json()["error"] == "not_found"


def test_holdings_do_not_depend_on_the_crm(mock_crm, db):
    mock_crm.set_mode("error")
    app = create_app(Settings(crm_base_url=mock_crm.base_url, crm_timeout_seconds=0.5), db=db)
    with TestClient(app) as client:
        assert client.get("/portfolios/P-9001").status_code == 502  # CRM-backed metadata is down...
        assert client.get("/portfolios/P-9001/holdings").status_code == 200  # ...holdings still work
