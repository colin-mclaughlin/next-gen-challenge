"""Injectable "today" so date-relative logic (history ranges, fixture freshness) is testable."""
from collections.abc import Callable
from datetime import UTC, date, datetime

Clock = Callable[[], date]


def utc_today() -> date:
    """Today's date in UTC, matching the dates written by backend/fixtures/generate-history.mjs."""
    return datetime.now(UTC).date()
