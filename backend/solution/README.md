# Portfolio Dashboard Backend

Python 3.12 with **FastAPI**. Persistence will use SQLite through Python's built-in `sqlite3` module, starting in Task 2.

## Requirements
- Python **3.11+** (developed on 3.12)
- Node.js, only to run the supplied mock CRM (`backend/mock-crm.mjs`). The HTTP tests start it automatically.

## Install
From `backend/solution/`:

```sh
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
```

## Run
From the repo root, in two terminals:

```sh
node backend/mock-crm.mjs                # mock CRM on :4002
cd backend/solution && python -m app     # this backend on :3000 (venv active)
```

Interactive API docs are at <http://localhost:3000/docs>.

| Env var | Default | Purpose |
|---|---|---|
| `PORT` | `3000` | Port this service listens on |
| `HOST` | `127.0.0.1` | Bind address |
| `CRM_BASE_URL` | `http://localhost:4002` | Mock CRM base URL |
| `CRM_TIMEOUT_MS` | `2000` | Total time limit for a CRM call (the mock's timeout mode hangs for 10s) |

## Test
```sh
cd backend/solution && python -m pytest
```
- `tests/unit/` covers pure logic with no network: the CRM mapper, and the CRM client using `httpx.MockTransport`.
- `tests/http/` starts the **real mock CRM** with `node` on a random port and calls the app through FastAPI's `TestClient`. CRM modes are switched with `POST /__control`. If `node` isn't on PATH, these tests are skipped.

## Layout
```
app/main.py           create_app(): wires settings, CRM client, services, routers, error handlers
app/__main__.py       `python -m app` runs uvicorn
app/config.py         Settings loaded from env vars
app/errors.py         ApiError + handlers that produce the { error, message } envelope
app/schemas.py        Pydantic response models (snake_case in Python, camelCase in JSON)
app/routers/          thin route definitions
app/services/         CRM client, CRM -> schema mapper, portfolio metadata service
tests/unit, tests/http
```

## API conventions
- Every error uses the same shape: `{ "error": "<code>", "message": "<human readable>" }`. This includes framework errors:
  - unknown route: `404 not_found`
  - wrong method: `405 method_not_allowed`
  - invalid input: **`400 bad_request`** (FastAPI's default 422 is overridden)
  - unexpected error: `500 internal_error`
- Percentages are decimals (`0.0032` = 0.32%).
- JSON field names are camelCase, matching the schemas in `backend/REQUIREMENTS.md`.

## Task notes and decisions

### Task 1: `GET /portfolios/{id}` (CRM metadata)
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

  Requests never hang: `asyncio.timeout` caps the whole CRM call, including reading the body. httpx's own timeouts only apply to each individual network operation.
- **P-9002 day change:** the CRM reports `dayChangePercent: 0` for P-9002 because its previous value is 0. Task 1 passes the CRM value through unchanged. The holdings calculation planned for Task 2 will return `null` when the previous close is 0.
- **Known limitations:**
  - A new `httpx.AsyncClient` is created for each CRM call. That's simple and safe, but it doesn't reuse connections. A shared client opened in the app's startup would.
  - Starlette 1.x warns that its `TestClient` prefers `httpx2`. The warning is filtered in `pyproject.toml`, and plain `httpx` works.
- **Not yet done:** caching and stale fallback (Task 9), auth (Task 4), currency conversion (Task 7).
