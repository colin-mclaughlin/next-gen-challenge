# Portfolio Dashboard Backend

Python 3.12 · **FastAPI** · **SQLAlchemy 2.0** on SQLite · httpx · Pydantic · pytest + mypy.

A layered API: routers → services → pure domain logic, with SQLAlchemy models and repositories for the database, and a dedicated client and mapper for the external CRM.
**Start with [docs/architecture.md](docs/architecture.md)** for how everything fits together.

## Endpoints
| Endpoint | Source | Notes |
|---|---|---|
| `GET /portfolios/{id}` | External CRM | [docs/task-01.md](docs/task-01.md) |
| `GET /portfolios/{id}/holdings` | Our database | [docs/task-02.md](docs/task-02.md) |
| `GET /portfolios/{id}/performance-history?range=1D\|1M\|YTD\|1Y\|All` | Our database | [docs/task-03.md](docs/task-03.md) |
| `GET /health` | — | Liveness check |

## Requirements
- Python **3.11+** (developed on 3.12)
- Node.js, to run the supplied mock CRM (`backend/mock-crm.mjs`) and the history generator. The HTTP tests start the mock automatically.

## Install
From `backend/solution/`:

```sh
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements-dev.txt     # app + test/type-check tools (requirements.txt = app only)
```

## Run
Two terminals. Paths are relative to the repo root (`nextgenchallenge/`):

```sh
node backend/mock-crm.mjs                # terminal 1: mock CRM on :4002
cd backend/solution && python -m app     # terminal 2: this backend on :3000 (venv active)
```

Open **<http://localhost:3000/docs>** (Swagger). The root URL `/` has no endpoint and returns a structured 404.

On start, the SQLite database (`data/app.db`) is rebuilt from the fixtures. If the performance-history sample is missing or out of date, it is regenerated first (needs Node).

| Env var | Default | Purpose |
|---|---|---|
| `PORT` | `3000` | Port this service listens on |
| `HOST` | `127.0.0.1` | Bind address |
| `CRM_BASE_URL` | `http://localhost:4002` | Mock CRM base URL |
| `CRM_TIMEOUT_MS` | `2000` | Total time limit for a CRM call (the mock's timeout mode hangs for 10 s) |
| `DATABASE_PATH` | `data/app.db` | SQLite file, rebuilt on start (`:memory:` also works) |
| `SEED_PATH` | `backend/fixtures/seed.json` | Fixture data loaded into the database |
| `HISTORY_PATH` | `backend/fixtures/performance-history.json` | Daily history. The default file is regenerated at startup if missing or stale. |

## Trying it in Swagger
On `/docs`: open an endpoint → **Try it out** → fill in `portfolio_id` (and `range`) → **Execute**.

Useful inputs: `P-9001` (mixed assets, zero-quantity `ZERO`), `P-9002` (`NEW` has a zero previous close, 60 days of history), `P-SINGLE` (one holding), `P-EMPTY` (no holdings or history), `UNKNOWN` (404).

The mock CRM fails on purpose every 5th call (502) and every 10th (504). To choose its behaviour, run in another terminal:
```powershell
Invoke-RestMethod -Method Post http://localhost:4002/__control -ContentType 'application/json' -Body '{"mode":"ok"}'
```
Modes: `ok`, `error` (→ 502), `timeout` (→ 504 after about 2 s), `missing` (→ nulls), `nested`, `auto` (default pattern).

## Test and type-check
```sh
cd backend/solution && python -m pytest && python -m mypy
```
- `tests/unit/`: pure logic with no network: calculations and date ranges, CRM mapper/client/service, models, seeding.
- `tests/http/`: every endpoint through FastAPI's `TestClient`, backed by a fresh in-memory database. CRM tests start the **real mock CRM** with `node` on a random port and switch its modes; they are skipped if `node` isn't on PATH.
- `mypy` type-checks all of `app/`.
- [tests/TASK1_TESTS.md](tests/TASK1_TESTS.md) explains each CRM test case.

## Layout
```
app/
  main.py          create_app(): composition root; wires engine, sessions, CRM client, services, routers, errors
  __main__.py      `python -m app` runs uvicorn
  config.py        Settings from environment variables
  clock.py         injectable "today" (UTC)
  errors.py        ApiError + handlers producing the { error, message } envelope
  schemas.py       Pydantic response models (snake_case in Python, camelCase in JSON)
  routers/         HTTP edge, one file per feature
  services/        use cases + CRM client and mapper
  domain/          pure calculations (no I/O): holdings valuation, history ranges, rounding
  models/          SQLAlchemy models: one class per table, relationships, constraints
  db/              engine, sessions, repositories (all queries), build + seed, generated schema.sql
tests/
  conftest.py      shared fixtures (in-memory DB, mock CRM, pinned date)
  unit/, http/
docs/
  architecture.md  how the system works (start here)
  task-0N.md       per-endpoint decisions
```

## Common commands
| Command | Does |
|---|---|
| `python -m app` | Run the API |
| `python -m pytest` | Run all tests |
| `python -m mypy` | Type-check `app/` |
| `python -m app.db.schema_dump` | Regenerate `app/db/schema.sql` after changing a model |

## API conventions
- Every error uses one shape: `{ "error": "<code>", "message": "<human readable>" }`, including framework errors (unknown route `404 not_found`, wrong method `405 method_not_allowed`, invalid input **`400 bad_request`** instead of FastAPI's 422, unexpected `500 internal_error`).
- Percentages are decimals (`0.0032` = 0.32%). Seed money is CAD. Undefined values are `null`, never an invented `0`.
- JSON field names are camelCase, matching `backend/REQUIREMENTS.md`.

## Scope
Implements requirements Tasks 1–3. Not implemented: authentication, currency conversion, allocation, household views, holding detail, CRM caching and ledger replay (REQUIREMENTS Tasks 4–10). [Architecture §11](docs/architecture.md#11-how-to-add-a-new-endpoint) is the recipe for adding them; §8 covers how authentication would plug in.

## Working on this repo
- One branch and one PR per change; collaborator follow-ups in their own small branches (`collab/...`).
- Run `git pull --rebase origin main` before starting a branch.
- Add routes as new files in `app/routers/` and notes as new files in `docs/`, so parallel work rarely touches the same lines.
