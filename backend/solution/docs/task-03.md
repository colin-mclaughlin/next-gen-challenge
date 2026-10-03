# Task 3: `GET /portfolios/{id}/performance-history?range=`

Code: `app/domain/history.py` (pure range logic), `app/services/history.py`, `app/routers/history.py`, `app/db/repositories.py` (`list_snapshots`), `app/models/performance.py`, `app/db/history_fixture.py` (keeps the sample file current), `app/clock.py`. See [architecture.md](architecture.md) for how the layers connect.
Tests: `tests/unit/test_history_range.py`, `tests/unit/test_history_fixture.py`, `tests/http/test_performance_history.py`.

## Range rules
Each range returns daily snapshots with `start ≤ date ≤ today`, oldest first. "Today" is the **UTC** date, which matches the dates `generate-history.mjs` writes.

| `range` | Start date (example: today = 2026-10-03) |
|---|---|
| `1D` | Yesterday (2026-10-02). With daily data that's 2 points: yesterday's and today's. |
| `1M` | The same day last month (2026-09-03), clamped to the month's end (Mar 31 → Feb 28/29) |
| `YTD` | **Jan 1 of the current year** (2026-01-01), not the earliest data available |
| `1Y` | The same day last year (2025-10-03). Feb 29 → Feb 28. |
| `All` (default) | No lower bound |

## Decisions
- **Strict values:** `range` must match exactly. `ytd`, `5Y` and an empty `?range=` all return `400 {"error": "invalid_range", ...}` listing the allowed values. It never falls back to a default silently. Omitting the parameter entirely means `All`.
- **Input is checked before the lookup:** an invalid `range` returns 400 even for an unknown portfolio, because the request itself is malformed. A valid range with an unknown id returns `404 portfolio_not_found`.
- **Less history than the range:** return what exists, with no padding and no error. P-9002 has 60 days, so `1Y` returns 60 points. P-EMPTY returns `[]`.
- **`marketValue`** is rounded to 2 decimal places with the shared `round_money` helper.
- **Testable dates:** the clock is injectable (`create_app(clock=...)`). Tests pin "today" to 2026-10-03 and generate matching history, so they never depend on the real date.

## Sample data lifecycle
- History comes from `backend/fixtures/performance-history.json`, produced by `node backend/fixtures/generate-history.mjs` with dates ending on the day it runs.
- **Automatic refresh:** at startup, if that file is missing or its newest date is before today, the app re-runs the generator before building the database. That keeps YTD and 1D on the current dates without anyone having to remember to regenerate.
  - If Node isn't available, startup logs a warning and continues with whatever history exists, possibly none.
  - The refresh only applies to the default path. A custom `HISTORY_PATH` is loaded as-is.
- **Validation:** history for a portfolio id that isn't in the seed fails loudly at startup.
- **Git:** the generated file is listed in the repo-root `.gitignore`. START-HERE says it's ignored, but this repo had no rule for it.
- **Schema:** model `PerformanceSnapshot` → table `performance_snapshots(portfolio_id FK, date, market_value CHECK ≥ 0, PK(portfolio_id, date))`.
