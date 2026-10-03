"""Performance history ranges (Task 3): pure date logic, no I/O."""
import calendar
from dataclasses import dataclass
from datetime import date, timedelta

RANGES = ("1D", "1M", "YTD", "1Y", "All")
DEFAULT_RANGE = "All"


@dataclass(frozen=True)
class Snapshot:
    date: str  # ISO 8601 YYYY-MM-DD
    market_value: float


class InvalidRange(ValueError):
    pass


def parse_range(raw: str | None) -> str:
    """Validate the `range` query value. Omitted -> "All"; anything else must match exactly."""
    if raw is None:
        return DEFAULT_RANGE
    if raw not in RANGES:
        raise InvalidRange(f"range must be one of: {', '.join(RANGES)} (got {raw!r}).")
    return raw


def range_start(range_: str, today: date) -> date | None:
    """First date (inclusive) covered by `range_`, ending today. None means no lower bound ("All").

    1D  -> yesterday (daily data: yesterday's close and today's)
    1M  -> same day last month, clamped to month end (Mar 31 -> Feb 28/29)
    YTD -> January 1 of today's year
    1Y  -> same day last year (Feb 29 -> Feb 28)
    """
    if range_ == "1D":
        return today - timedelta(days=1)
    if range_ == "1M":
        return minus_months(today, 1)
    if range_ == "YTD":
        return date(today.year, 1, 1)
    if range_ == "1Y":
        return minus_months(today, 12)
    if range_ == "All":
        return None
    raise InvalidRange(f"range must be one of: {', '.join(RANGES)} (got {range_!r}).")


def minus_months(day: date, months: int) -> date:
    """Calendar-month subtraction, clamping the day to the target month's length."""
    year, month_index = divmod(day.year * 12 + (day.month - 1) - months, 12)
    month = month_index + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))
