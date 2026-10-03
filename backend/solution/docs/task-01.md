# Task 1: `GET /portfolios/{id}` (CRM metadata)

Code: `app/services/crm_client.py`, `app/services/crm_mapper.py`, `app/services/portfolio_metadata.py`, `app/routers/portfolios.py`.
Tests: `tests/unit/test_crm_mapper.py`, `tests/unit/test_crm_client.py`, `tests/http/test_portfolio_metadata.py`.

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

## Not yet done
- Caching and stale fallback (Task 9)
- Auth (Task 4)
- Currency conversion (Task 7)
