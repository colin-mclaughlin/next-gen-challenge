from datetime import date

import pytest

from app.domain.history import RANGES, InvalidRange, minus_months, parse_range, range_start

TODAY = date(2026, 10, 3)


@pytest.mark.parametrize(
    ("range_", "expected"),
    [
        ("1D", date(2026, 10, 2)),
        ("1M", date(2026, 9, 3)),
        ("YTD", date(2026, 1, 1)),  # January 1 of the current year, not the earliest data
        ("1Y", date(2025, 10, 3)),
        ("All", None),
    ],
)
def test_range_start(range_, expected):
    assert range_start(range_, TODAY) == expected


@pytest.mark.parametrize(
    ("day", "months", "expected"),
    [
        (date(2026, 3, 31), 1, date(2026, 2, 28)),  # clamp to shorter month
        (date(2028, 3, 31), 1, date(2028, 2, 29)),  # leap year
        (date(2028, 2, 29), 12, date(2027, 2, 28)),  # 1Y from Feb 29
        (date(2026, 1, 15), 1, date(2025, 12, 15)),  # crosses year boundary
        (date(2026, 1, 1), 12, date(2025, 1, 1)),
    ],
)
def test_minus_months_clamps_to_month_end(day, months, expected):
    assert minus_months(day, months) == expected


def test_ytd_on_january_first_is_just_today():
    assert range_start("YTD", date(2026, 1, 1)) == date(2026, 1, 1)


def test_parse_range_defaults_to_all():
    assert parse_range(None) == "All"


@pytest.mark.parametrize("value", RANGES)
def test_parse_range_accepts_every_documented_value(value):
    assert parse_range(value) == value


@pytest.mark.parametrize("value", ["", "invalid", "ytd", "1d", "all", " 1M", "5Y"])
def test_parse_range_rejects_anything_else(value):
    with pytest.raises(InvalidRange, match="range must be one of"):
        parse_range(value)
