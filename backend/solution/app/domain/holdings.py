"""Holding valuation (Task 2): pure calculations, no I/O. Values are unrounded; see rounding.py."""
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Position:
    """Stored inputs for one holding."""

    ticker: str
    name: str
    asset_class: str
    quantity: float
    cost_basis_per_share: float
    price: float
    previous_close_price: float


@dataclass(frozen=True)
class HoldingValuation:
    position: Position
    market_value: float
    weight_percent: float
    unrealized_gain_loss: float
    day_change_amount: float
    day_change_percent: float | None  # None when previous close is 0 (no meaningful % change)


def value_holdings(positions: list[Position]) -> list[HoldingValuation]:
    """Compute per-holding values, ordered by market value (largest first), then ticker.

    - weight = market value / portfolio total, or 0 when the total is 0 (e.g. only closed positions).
      Weights are not adjusted to sum to exactly 1.
    - day_change_percent is per share (a price move), so a zero-quantity holding still reports it.
    """
    # Convert stored inputs before arithmetic. Converting an already-computed float
    # at rounding time cannot recover an exact half-cent lost during subtraction.
    market_values = [Decimal(str(p.quantity)) * Decimal(str(p.price)) for p in positions]
    total = sum(market_values, Decimal(0))

    valuations = [
        HoldingValuation(
            position=p,
            market_value=_clean(market_value),
            weight_percent=_clean(market_value / total) if total else 0.0,
            unrealized_gain_loss=_clean(
                (Decimal(str(p.price)) - Decimal(str(p.cost_basis_per_share))) * Decimal(str(p.quantity))
            ),
            day_change_amount=_clean(
                (Decimal(str(p.price)) - Decimal(str(p.previous_close_price))) * Decimal(str(p.quantity))
            ),
            day_change_percent=day_change_percent(p.price, p.previous_close_price),
        )
        for p, market_value in zip(positions, market_values, strict=True)
    ]
    return sorted(valuations, key=lambda v: (-v.market_value, v.position.ticker))


def day_change_percent(price: float, previous_close: float) -> float | None:
    """(price - previous close) / previous close, or None when previous close is 0."""
    if previous_close == 0:
        return None
    current, previous = Decimal(str(price)), Decimal(str(previous_close))
    return _clean((current - previous) / previous)


def _clean(value: Decimal) -> float:
    """Return an unrounded numeric result with neutral zero for existing consumers."""
    return float(value) + 0.0
