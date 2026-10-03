"""Calculation tests for Task 2, independent of HTTP and the database. Expected values worked by hand."""
import math

import pytest

from app.domain.holdings import Position, day_change_percent, value_holdings
from app.domain.rounding import round_money, round_ratio

AAPL = Position("AAPL", "Apple Inc.", "Equity", 120, 200, 227.5, 225)
BND = Position("BND", "Vanguard Total Bond ETF", "Fixed Income", 300, 74, 72.1, 73)
ZERO = Position("ZERO", "Closed Position", "Equity", 0, 10, 12, 10)
NEW = Position("NEW", "New Security", "Equity", 10, 40, 50, 0)


def by_ticker(valuations):
    return {v.position.ticker: v for v in valuations}


def test_p9001_values_match_hand_calculation():
    result = by_ticker(value_holdings([AAPL, BND, ZERO]))

    aapl = result["AAPL"]
    assert aapl.market_value == 27300  # 120 x 227.5
    assert aapl.unrealized_gain_loss == 3300  # (227.5 - 200) x 120
    assert aapl.day_change_amount == 300  # (227.5 - 225) x 120
    assert aapl.day_change_percent == pytest.approx(2.5 / 225)
    assert aapl.weight_percent == pytest.approx(27300 / 48930)

    bnd = result["BND"]
    assert bnd.market_value == pytest.approx(21630)  # 300 x 72.1
    assert bnd.unrealized_gain_loss == pytest.approx(-570)  # (72.1 - 74) x 300
    assert bnd.day_change_amount == pytest.approx(-270)  # (72.1 - 73) x 300
    assert bnd.day_change_percent == pytest.approx(-0.9 / 73)
    assert bnd.weight_percent == pytest.approx(21630 / 48930)


def test_total_matches_crm_portfolio_value():
    assert sum(v.market_value for v in value_holdings([AAPL, BND, ZERO])) == pytest.approx(48930)


def test_zero_quantity_gives_zero_values_and_no_negative_zero():
    losing_zero = Position("LOSS", "Closed at a loss", "Equity", 0, 74, 72.1, 73)
    for v in value_holdings([AAPL, ZERO, losing_zero]):
        if v.position.quantity == 0:
            for value in (v.market_value, v.weight_percent, v.unrealized_gain_loss, v.day_change_amount):
                assert value == 0
                assert math.copysign(1, value) == 1, "must not be -0.0"


def test_zero_quantity_still_reports_per_share_price_move():
    (zero,) = value_holdings([ZERO])
    assert zero.day_change_percent == pytest.approx(0.2)  # (12 - 10) / 10


def test_zero_previous_close_gives_null_percent_but_still_computes_amount():
    (new,) = value_holdings([NEW])
    assert new.day_change_percent is None
    assert new.day_change_amount == 500  # (50 - 0) x 10
    assert day_change_percent(50, 0) is None


def test_empty_portfolio_returns_empty_list():
    assert value_holdings([]) == []


def test_all_zero_quantity_portfolio_has_zero_weights_without_dividing_by_zero():
    assert [v.weight_percent for v in value_holdings([ZERO])] == [0.0]


def test_single_holding_has_full_weight():
    assert [v.weight_percent for v in value_holdings([AAPL])] == [1.0]


def test_weights_are_not_forced_to_sum_to_one():
    thirds = [Position(t, t, "Equity", 1, 1, 1, 1) for t in ("A", "B", "C")]
    rounded = [round_ratio(v.weight_percent) for v in value_holdings(thirds)]
    assert rounded == [0.333333, 0.333333, 0.333333]  # sums to 0.999999 - expected, not corrected


def test_ordered_by_market_value_then_ticker():
    tied = Position("AAA", "Tie", "Equity", 1, 1, 27300, 27300)
    assert [v.position.ticker for v in value_holdings([ZERO, BND, AAPL, tied])] == ["AAA", "AAPL", "BND", "ZERO"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [(2.675, 2.68), (21630.000000000004, 21630.0), (-0.001, 0.0), (-570.0000000000003, -570.0)],
)
def test_round_money_is_half_up_and_never_negative_zero(value, expected):
    result = round_money(value)
    assert result == expected
    assert math.copysign(1, result) == math.copysign(1, expected)
