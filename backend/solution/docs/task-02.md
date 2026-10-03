# Task 2: `GET /portfolios/{id}/holdings` (holdings, valuation, gain/loss)

Code: `app/domain/holdings.py` (pure calculations), `app/domain/rounding.py`, `app/services/holdings.py`, `app/routers/holdings.py`, `app/db/` (schema, seeding, queries).
Tests: `tests/unit/test_holdings_calc.py`, `tests/unit/test_database.py`, `tests/http/test_holdings.py`.

## Calculations
Every calculated field is computed per request from stored inputs (quantity, cost basis, price, previous close). Nothing calculated is stored.

| Field | Formula | Edge case |
|---|---|---|
| `marketValue` | `quantity × price` | |
| `weightPercent` | `marketValue / Σ marketValue` (decimal) | `0` if the portfolio total is 0. Not adjusted to sum to 1. |
| `unrealizedGainLoss` | `(price − costBasisPerShare) × quantity` | |
| `dayChangeAmount` | `(price − previousClosePrice) × quantity` | Still computed when the previous close is 0 (NEW: `500`) |
| `dayChangePercent` | `(price − previousClosePrice) / previousClosePrice` | **`null` when the previous close is 0** |

## Decisions
- **Previous close of 0 gives `null`, not `0`:**
  - A percentage change from 0 is undefined, and `0` would wrongly claim "no change". NEW rose from 0 to 50.
  - `null` lets clients show "n/a".
  - The CRM reports `0` for P-9002 at portfolio level (Task 1). That's the CRM's value, passed through unchanged.
- **Zero quantity:** `marketValue`, `weightPercent`, `unrealizedGainLoss` and `dayChangeAmount` are all `0`, never `-0`.
  - `dayChangePercent` is a per-share price move, so ZERO still reports `0.2`. It's information about the security, not the position.
- **Rounding happens only at output.** Calculations use unrounded values, which keeps totals and weights consistent.
  - Money: 2 decimal places, rounded half-up.
  - Ratios (`weightPercent`, `dayChangePercent`): 6 decimal places.
  - Stored inputs (`quantity`, prices, cost basis) are returned as stored.
  - The rounding helpers live in `app/domain/rounding.py` so Task 7's currency conversion can reuse them.
- **Order:** by `marketValue`, largest first, then by ticker, so the dashboard table order is stable.
- **404:** an unknown portfolio id is checked against our **database**, not the CRM, so holdings keep working while the CRM is down. A test covers this.
- **Numbers in JSON** are floats (`120.0`), which is the same value as `120` to any JSON client.

## Database (`app/db/`)
- **Schema:** `schema.sql`, normalized, with foreign keys enforced (`PRAGMA foreign_keys = ON`) and CHECK constraints.

  | Table | Holds |
  |---|---|
  | `clients` | `client_id`, `name` |
  | `portfolios` | `portfolio_id`, `client_id` (FK), `label`, `currency` |
  | `securities` | Security master: name, asset class, sector, dividend yield, 52-week range, price and previous close |
  | `security_price_history` | Daily prices per ticker |
  | `holdings` | `portfolio_id` (FK), `ticker` (FK), plus snapshot `quantity` and `cost_basis_per_share` |
  | `transactions` | BUY/SELL ledger per holding |
  | `exchange_rates` | Currency pairs and rates |

- **Why a `securities` table:** prices belong to a security, not a holding. AAPL is held in P-9001 and P-SINGLE, so it's stored once.
  - If two seed holdings of the same ticker disagree on price, seeding fails loudly.
- **Snapshot columns:** `holdings.quantity` and `holdings.cost_basis_per_share` come from the seed, as START-HERE allows for Tasks 2–9. Task 10 replaces them with values replayed from `transactions`.
- **Lifecycle:** `data/app.db` (gitignored) is a disposable copy of `backend/fixtures/seed.json`. It's **deleted and rebuilt on every startup**, so every run starts from the same known state. Tests use `:memory:`. Override with `DATABASE_PATH` and `SEED_PATH`.
- **Threading:** one shared connection (`check_same_thread=False`).
  - Every route that touches it is `async`, so access stays on the event-loop thread and is never concurrent.
  - The queries are small local reads, so blocking the loop briefly is acceptable here.
  - A larger service would use a connection per request or a pool.
