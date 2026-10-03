# Portfolio Dashboard Backend

Python 3.12 with **FastAPI**. Persistence is SQLite through **SQLAlchemy 2.0**: models in `app/models/`, queries in `app/db/repositories.py`.

## Requirements
- Python **3.11+** (developed on 3.12)
- Node.js, only to run the supplied mock CRM (`backend/mock-crm.mjs`). The HTTP tests start it automatically.

## Install
From `backend/solution/`:

```sh
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements-dev.txt     # app + test/type-check tools (requirements.txt = app only)
```

## Run
From the repo root, in two terminals:

```sh
node backend/mock-crm.mjs                # mock CRM on :4002
cd backend/solution && python -m app     # this backend on :3000 (venv active)
```

Interactive API docs are at <http://localhost:3000/docs>. The SQLite database (`data/app.db`) is rebuilt from the fixtures on every start. If the performance history sample is missing or out of date, it's regenerated first (needs Node).

| Env var | Default | Purpose |
|---|---|---|
| `PORT` | `3000` | Port this service listens on |
| `HOST` | `127.0.0.1` | Bind address |
| `CRM_BASE_URL` | `http://localhost:4002` | Mock CRM base URL |
| `CRM_TIMEOUT_MS` | `2000` | Total time limit for a CRM call (the mock's timeout mode hangs for 10s) |
| `DATABASE_PATH` | `data/app.db` | SQLite file, rebuilt on start (`:memory:` also works) |
| `SEED_PATH` | `backend/fixtures/seed.json` | Fixture data loaded into the database |
| `HISTORY_PATH` | `backend/fixtures/performance-history.json` | Daily history. The default file is regenerated at startup if it's missing or stale. |

## Test and type-check
```sh
cd backend/solution && python -m pytest && python -m mypy
```
- `tests/unit/` covers pure logic with no network: calculations, the CRM mapper and client, and database seeding.
- `tests/http/` calls the app through FastAPI's `TestClient`, backed by a seeded in-memory database.
  - CRM tests start the **real mock CRM** with `node` on a random port and switch its modes with `POST /__control`.
  - If `node` isn't on PATH, the CRM tests are skipped.
- `mypy` checks the type hints in `app/`.
- Run just the unit tests with `python -m pytest tests/unit -v`. [Task 1 test rationale](tests/TASK1_TESTS.md) explains each added case.

## Layout
```
app/main.py           create_app(): wires settings, CRM client, database, services, routers, error handlers
app/__main__.py       `python -m app` runs uvicorn
app/config.py         Settings loaded from env vars
app/clock.py          injectable "today" (UTC) for date-relative logic
app/errors.py         ApiError + handlers that produce the { error, message } envelope
app/schemas.py        Pydantic response models (snake_case in Python, camelCase in JSON)
app/routers/          thin route definitions, one file per feature
app/services/         orchestration: CRM client and mapper, portfolio metadata, holdings, history
app/domain/           pure calculations (no I/O): holdings valuation, history ranges, rounding
app/models/           SQLAlchemy models: one class per table, with relationships and constraints
app/db/               engine + sessions, database build/seed, repositories (all queries), generated schema.sql
tests/unit, tests/http
docs/task-NN.md       per-task decisions and notes
```

## API conventions
- Every error uses the same shape: `{ "error": "<code>", "message": "<human readable>" }`. This includes framework errors:
  - unknown route: `404 not_found`
  - wrong method: `405 method_not_allowed`
  - invalid input: **`400 bad_request`** (FastAPI's default 422 is overridden)
  - unexpected error: `500 internal_error`
- Percentages are decimals (`0.0032` = 0.32%). All seed money is CAD.
- JSON field names are camelCase, matching the schemas in `backend/REQUIREMENTS.md`.

## Tasks
| Task | Endpoint | Notes |
|---|---|---|
| 1 | `GET /portfolios/{id}` | [docs/task-01.md](docs/task-01.md) |
| 2 | `GET /portfolios/{id}/holdings` | [docs/task-02.md](docs/task-02.md) |
| 3 | `GET /portfolios/{id}/performance-history?range=` | [docs/task-03.md](docs/task-03.md) |

## Working on this repo
- **One branch and one PR per task** (`task-NN-name`). Collaborator follow-ups go in their own small branches (`collab/...`).
- Run `git pull --rebase origin main` before starting a branch.
- Add new routes as new files in `app/routers/`, and new notes as new `docs/task-NN.md` files, so parallel work rarely touches the same lines.
