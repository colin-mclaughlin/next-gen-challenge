# Task 1: `GET /portfolios/{id}` (CRM metadata)

Code: `app/services/crm_client.py`, `app/services/crm_mapper.py`, `app/services/portfolio_metadata.py`, `app/routers/portfolios.py`.
Tests: `tests/unit/test_crm_mapper.py`, `tests/unit/test_crm_client.py`, `tests/unit/test_portfolio_metadata_service.py`, `tests/http/test_portfolio_metadata.py` (case-by-case rationale in [`tests/TASK1_TESTS.md`](../tests/TASK1_TESTS.md)).

This is the only endpoint that depends on the external CRM; the others read from our database.

## Decisions
- **Account selection:** the CRM returns *all* of a client's accounts. We match on `acct_ref` and never assume the first one.
- **Inconsistent nesting:** accounts are read from `client_record.accounts` or, failing that, `client_record.relationships.accounts`.
- **Missing values:** missing, null or non-numeric values map to `null` and are never replaced with `0`. In `?mode=missing`, P-9001 returns `label: null, totalMarketValue: null`. A genuine `0` stays `0`. Numeric strings such as `"100.5"` are accepted, and booleans are rejected.
  - A missing `curr_val.ccy` defaults to `CAD`, the platform base currency per the requirements.
  - An unparseable `meta.retrieved_at` gives `asOf: null`. Valid values are normalised to ISO 8601 UTC, for example `2025-06-01T10:00:00.000Z`.
- **Structurally broken payload:** if `client_record`, the accounts list, or `client_id` is missing, the response is `502 bad_crm_response`.
- **Failure mapping:**

  | CRM outcome | Our response |
  |---|---|
  | 404, or the account isn't in the payload | `404 portfolio_not_found` |
  | 5xx or network error | `502 crm_unavailable` |
  | No response within `CRM_TIMEOUT_MS`, or CRM 504 | `504 crm_timeout` |

- **Requests never hang:** `asyncio.timeout` caps the whole CRM call, including reading the body. httpx's own timeouts only apply to each individual network operation.
- **Shared HTTP client:** one `httpx.AsyncClient` is created on first use and closed when the app shuts down.
  - It reuses connections.
  - Its SSL context is built once, outside the timed section. Building it inside the timer caused false timeouts on Windows (fixed during Task 2).
- **P-9002 day change:** the CRM reports `dayChangePercent: 0` for P-9002 because its previous value is 0. Task 1 passes the CRM value through unchanged. The holdings endpoint (Task 2) returns `null` when the previous close is 0.

## Out of scope (possible extensions)
- **Caching with stale fallback** (REQUIREMENTS Task 9). It would wrap `PortfolioMetadataService.get()`: serve fresh cached values within a TTL, and fall back to the last good value when `crm_client` reports `timeout` or `unavailable`. The client's failure classification already supports this.
- **Authentication** (Task 4): see [architecture §8](architecture.md#8-security-posture).
- **Currency conversion** (Task 7). `exchange_rates` is already seeded, and the rounding helpers in `app/domain/rounding.py` would be reused.
