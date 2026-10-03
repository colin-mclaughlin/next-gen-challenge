"""Calculation tests for Task 2, independent of HTTP and the database. Expected values worked by hand."""
import math
from dataclasses import replace

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


@pytest.mark.parametrize(
    ("price", "cost", "expected_market_value", "expected_change"),
    [(0.3, 0.2, 0.05, 0.02), (0.2, 0.3, 0.03, -0.02)],
)
def test_fractional_positions_round_half_cent_gains_and_losses_correctly(price, cost, expected_market_value, expected_change):
    position = Position("FRAC", "Fractional position", "Equity", 0.15, cost, price, cost)
    (value,) = value_holdings([position])
    # (0.30 - 0.20) * 0.15 = 0.015, which rounds half-up to 0.02.
    assert round_money(value.market_value) == expected_market_value
    assert round_money(value.unrealized_gain_loss) == expected_change
    assert round_money(value.day_change_amount) == expected_change
    assert value.weight_percent == 1


def test_zero_price_with_positive_quantity_has_zero_weight_and_full_loss():
    position = Position("WORTHLESS", "Worthless security", "Equity", 2, 4, 0, 10)
    (value,) = value_holdings([position])
    assert value.market_value == 0
    assert value.weight_percent == 0
    assert value.unrealized_gain_loss == -8
    assert value.day_change_amount == -20
    assert value.day_change_percent == -1


def test_unchanged_price_and_cost_have_neutral_changes():
    (value,) = value_holdings([Position("FLAT", "Flat security", "Cash", 3.5, 1, 1, 1)])
    assert value.market_value == 3.5
    assert value.unrealized_gain_loss == 0
    assert value.day_change_amount == 0
    assert value.day_change_percent == 0


def test_zero_price_and_zero_previous_close_remain_undefined():
    assert day_change_percent(0, 0) is None


def test_tiny_position_is_retained_even_when_display_weight_rounds_to_zero():
    tiny = Position("TINY", "Tiny security", "Equity", 0.001, 0.01, 0.01, 0.01)
    large = Position("LARGE", "Large security", "Equity", 1, 100, 100, 100)
    values = by_ticker(value_holdings([tiny, large]))
    assert len(values) == 2
    assert values["TINY"].market_value == pytest.approx(0.00001)
    assert values["TINY"].weight_percent > 0
    assert round_ratio(values["TINY"].weight_percent) == 0


def test_valuation_does_not_reorder_or_mutate_input_positions():
    positions = [ZERO, BND, AAPL]
    original = list(positions)
    value_holdings(positions)
    assert positions == original


def test_scaling_quotes_preserves_weights_and_price_change_percentages():
    original = value_holdings([AAPL, BND])
    scaled = value_holdings([
        replace(p, price=p.price * 10, cost_basis_per_share=p.cost_basis_per_share * 10,
                previous_close_price=p.previous_close_price * 10)
        for p in [AAPL, BND]
    ])
    for before, after in zip(original, scaled, strict=True):
        assert after.weight_percent == pytest.approx(before.weight_percent)
        assert after.day_change_percent == pytest.approx(before.day_change_percent)
        assert after.market_value == pytest.approx(before.market_value * 10)
        assert after.unrealized_gain_loss == pytest.approx(before.unrealized_gain_loss * 10)
        assert after.day_change_amount == pytest.approx(before.day_change_amount * 10)


@pytest.mark.parametrize(
    ("ratio", "expected"),
    [(None, None), (0, 0), (0.0000005, 0.000001), (-0.0000005, -0.000001), (-0.0000001, 0)],
)
def test_ratio_rounding_preserves_null_half_up_and_neutral_zero(ratio, expected):
    result = round_ratio(ratio)
    assert result == expected
    if result == 0:
        assert math.copysign(1, result) == 1
