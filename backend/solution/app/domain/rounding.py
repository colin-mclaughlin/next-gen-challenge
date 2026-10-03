"""Output rounding. Calculations run on unrounded values; round only when building a response."""
from decimal import ROUND_HALF_UP, Decimal

MONEY_PLACES = 2
RATIO_PLACES = 6


def round_to(value: float, places: int) -> float:
    """Round half-up (the convention people expect for money) and never return -0.0."""
    # repr() gives the shortest decimal string for the float, so 2.675 rounds to 2.68 as written,
    # instead of 2.67 from binary floating-point artefacts.
    quantum = Decimal(1).scaleb(-places)
    return float(Decimal(repr(value)).quantize(quantum, rounding=ROUND_HALF_UP)) + 0.0


def round_money(value: float) -> float:
    return round_to(value, MONEY_PLACES)


def round_ratio(value: float | None) -> float | None:
    return None if value is None else round_to(value, RATIO_PLACES)
