"""End-to-end tests for GET /portfolios/{id}/holdings (seeded in-memory SQLite)."""
import math

import pytest
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


def test_holdings_do_not_depend_on_the_crm(mock_crm, engine):
    mock_crm.set_mode("error")
    app = create_app(Settings(crm_base_url=mock_crm.base_url, crm_timeout_seconds=0.5), engine=engine)
    with TestClient(app) as client:
        assert client.get("/portfolios/P-9001").status_code == 502  # CRM-backed metadata is down...
        assert client.get("/portfolios/P-9001/holdings").status_code == 200  # ...holdings still work


def test_every_calculated_field_is_recomputed_after_stored_inputs_change(app_client, db):
    assert holdings(app_client, "P-9001")[1][0]["marketValue"] == 27300
    db.execute("UPDATE securities SET price = 250, previous_close_price = 240 WHERE ticker = 'AAPL'")
    db.execute("UPDATE holdings SET quantity = 0.5, cost_basis_per_share = 210 WHERE holding_id = 'h1'")
    db.commit()

    status, body = holdings(app_client, "P-9001")
    assert status == 200
    assert [row["ticker"] for row in body] == ["BND", "AAPL", "ZERO"]
    aapl = next(row for row in body if row["ticker"] == "AAPL")
    assert aapl == {
        "ticker": "AAPL", "name": "Apple Inc.", "assetClass": "Equity",
        "quantity": 0.5, "costBasisPerShare": 210, "price": 250, "previousClosePrice": 240,
        "marketValue": 125, "weightPercent": 0.005746, "unrealizedGainLoss": 20,
        "dayChangeAmount": 5, "dayChangePercent": 0.041667,
    }
    assert body[0]["weightPercent"] == 0.994254
    assert sum(row["marketValue"] for row in body) == 21755


def test_same_security_uses_account_specific_quantity_and_cost(app_client, db):
    db.execute("UPDATE holdings SET cost_basis_per_share = 100 WHERE holding_id = 'h5'")
    db.commit()
    first = next(row for row in holdings(app_client, "P-9001")[1] if row["ticker"] == "AAPL")
    status, second = holdings(app_client, "P-SINGLE")
    assert status == 200
    assert len(second) == 1
    assert (first["quantity"], first["costBasisPerShare"], first["marketValue"], first["unrealizedGainLoss"]) == (120, 200, 27300, 3300)
    assert (second[0]["quantity"], second[0]["costBasisPerShare"], second[0]["marketValue"], second[0]["unrealizedGainLoss"]) == (10, 100, 2275, 1275)
    assert [row["ticker"] for row in holdings(app_client, "P-9002")[1]] == ["NEW"]


@pytest.mark.parametrize("zero_field", ["quantity", "price"])
def test_zero_total_portfolio_returns_positions_with_finite_zero_weights(app_client, db, zero_field):
    if zero_field == "quantity":
        db.execute("UPDATE holdings SET quantity = 0 WHERE portfolio_id = 'P-9001'")
    else:
        db.execute("UPDATE securities SET price = 0")
    db.commit()

    status, body = holdings(app_client, "P-9001")
    assert status == 200
    assert len(body) == 3
    for row in body:
        assert row["marketValue"] == 0
        assert row["weightPercent"] == 0
        for value in row.values():
            if isinstance(value, (int, float)):
                assert math.isfinite(value)
                if value == 0:
                    assert math.copysign(1, value) == 1
    if zero_field == "quantity":
        assert all(row["unrealizedGainLoss"] == row["dayChangeAmount"] == 0 for row in body)
    else:
        assert next(row for row in body if row["ticker"] == "AAPL")["unrealizedGainLoss"] == -24000


@pytest.mark.parametrize(("price", "cost", "change"), [(0.3, 0.2, 0.02), (0.2, 0.3, -0.02)])
def test_fractional_half_cent_changes_are_rounded_correctly_in_json(app_client, db, price, cost, change):
    db.execute("UPDATE securities SET price = ?, previous_close_price = ? WHERE ticker = 'NEW'", (price, cost))
    db.execute("UPDATE holdings SET quantity = 0.15, cost_basis_per_share = ? WHERE holding_id = 'h4'", (cost,))
    db.commit()
    status, body = holdings(app_client, "P-9002")
    assert status == 200
    assert body[0]["quantity"] == 0.15
    assert body[0]["unrealizedGainLoss"] == change
    assert body[0]["dayChangeAmount"] == change


def test_rounded_weights_are_not_corrected_in_endpoint_response(app_client, db):
    db.execute("UPDATE securities SET price = 1, previous_close_price = 1")
    db.executemany(
        "INSERT INTO holdings VALUES (?, 'P-EMPTY', ?, 1, 1)",
        [("third-a", "AAPL"), ("third-b", "BND"), ("third-c", "NEW")],
    )
    db.commit()
    status, body = holdings(app_client, "P-EMPTY")
    assert status == 200
    assert [row["weightPercent"] for row in body] == [0.333333] * 3


def test_large_portfolio_returns_every_position_without_duplicates(app_client, db):
    tickers = [f"DEMO{i:02}" for i in range(60)]
    db.executemany(
        "INSERT INTO securities (ticker, name, asset_class, price, previous_close_price) VALUES (?, ?, 'Equity', 2, 1)",
        [(ticker, ticker) for ticker in tickers],
    )
    db.executemany(
        "INSERT INTO holdings VALUES (?, 'P-EMPTY', ?, 0.5, 1)",
        [(f"holding-{ticker}", ticker) for ticker in tickers],
    )
    db.commit()
    status, body = holdings(app_client, "P-EMPTY")
    assert status == 200
    assert [row["ticker"] for row in body] == tickers
    assert all(set(row) == FIELDS for row in body)
    assert all(row["marketValue"] == 1 and row["unrealizedGainLoss"] == 0.5 for row in body)
    assert all(row["weightPercent"] == 0.016667 for row in body)


def test_wrong_method_returns_structured_405(app_client):
    response = app_client.post("/portfolios/P-9001/holdings")
    assert response.status_code == 405
    assert response.json() == {"error": "method_not_allowed", "message": "Method Not Allowed"}
