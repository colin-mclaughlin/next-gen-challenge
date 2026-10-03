"""End-to-end tests for GET /portfolios/{id}/performance-history (history ends FIXED_TODAY = 2026-10-03)."""
import re

import pytest

from conftest import FIXED_TODAY

URL = "/portfolios/{id}/performance-history"


def history(client, portfolio_id, range_=None):
    params = {} if range_ is None else {"range": range_}
    res = client.get(URL.format(id=portfolio_id), params=params)
    return res.status_code, res.json()


@pytest.mark.parametrize(
    ("range_", "count", "first_date"),
    [
        ("All", 401, "2025-08-29"),  # 2026-10-03 minus 400 days
        ("1Y", 366, "2025-10-03"),
        ("YTD", 276, "2026-01-01"),  # Jan 1 of the current year, not the earliest snapshot
        ("1M", 31, "2026-09-03"),
        ("1D", 2, "2026-10-02"),
    ],
)
def test_each_range_filters_p9001(history_client, range_, count, first_date):
    status, body = history(history_client, "P-9001", range_)
    assert status == 200
    assert len(body) == count
    assert body[0]["date"] == first_date
    assert body[-1]["date"] == FIXED_TODAY.isoformat()


def test_points_have_the_documented_shape_and_ascending_dates(history_client):
    _, body = history(history_client, "P-9001")
    assert all(set(p) == {"date", "marketValue"} for p in body)
    assert all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", p["date"]) for p in body)
    dates = [p["date"] for p in body]
    assert dates == sorted(dates)
    assert body[-1]["marketValue"] == 48930  # generator ends at the portfolio's current value


def test_omitting_range_defaults_to_all(history_client):
    assert history(history_client, "P-9001") == history(history_client, "P-9001", "All")


@pytest.mark.parametrize(
    ("range_", "count", "first_date"),
    [("1Y", 60, "2026-08-05"), ("YTD", 60, "2026-08-05"), ("All", 60, "2026-08-05"), ("1M", 31, "2026-09-03")],
)
def test_less_history_than_range_returns_what_exists(history_client, range_, count, first_date):
    status, body = history(history_client, "P-9002", range_)  # only 60 days of history: no padding, no error
    assert status == 200
    assert len(body) == count
    assert body[0]["date"] == first_date


def test_portfolio_with_no_history_returns_empty_array(history_client):
    assert history(history_client, "P-EMPTY", "1Y") == (200, [])


@pytest.mark.parametrize("bad", ["invalid", "ytd", "", "5Y"])
def test_invalid_range_returns_structured_400(history_client, bad):
    status, body = history(history_client, "P-9001", bad)
    assert status == 400
    assert body["error"] == "invalid_range"
    assert "1D, 1M, YTD, 1Y, All" in body["message"]


def test_unknown_portfolio_returns_404(history_client):
    status, body = history(history_client, "UNKNOWN", "1Y")
    assert status == 404
    assert body["error"] == "portfolio_not_found"


def test_invalid_range_wins_over_unknown_portfolio(history_client):
    assert history(history_client, "UNKNOWN", "bogus")[0] == 400
