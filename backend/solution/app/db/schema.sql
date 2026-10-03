-- Normalized schema for the portfolio dashboard (all money in the portfolio's currency; seed data is CAD).
-- Foreign keys are enabled per connection in database.py (PRAGMA foreign_keys = ON).

CREATE TABLE clients (
    client_id TEXT PRIMARY KEY,
    name      TEXT NOT NULL
);

CREATE TABLE portfolios (
    portfolio_id TEXT PRIMARY KEY,
    client_id    TEXT NOT NULL REFERENCES clients (client_id),
    label        TEXT NOT NULL,
    currency     TEXT NOT NULL CHECK (length(currency) = 3)
);
CREATE INDEX idx_portfolios_client ON portfolios (client_id);

-- Security master: one row per ticker, shared by every portfolio that holds it (e.g. AAPL).
CREATE TABLE securities (
    ticker               TEXT PRIMARY KEY,
    name                 TEXT NOT NULL,
    asset_class          TEXT NOT NULL,
    sector               TEXT,
    dividend_yield       REAL CHECK (dividend_yield IS NULL OR dividend_yield >= 0),  -- NULL = pays no dividend
    fifty_two_week_low   REAL,
    fifty_two_week_high  REAL,
    price                REAL NOT NULL CHECK (price >= 0),
    previous_close_price REAL NOT NULL CHECK (previous_close_price >= 0)
);

CREATE TABLE security_price_history (
    ticker TEXT NOT NULL REFERENCES securities (ticker),
    date   TEXT NOT NULL,  -- ISO 8601 YYYY-MM-DD
    price  REAL NOT NULL CHECK (price >= 0),
    PRIMARY KEY (ticker, date)
);

-- A portfolio's position in one security.
-- quantity / cost_basis_per_share are seed snapshots used by Tasks 2-9 (allowed by START-HERE.md);
-- Task 10 derives them from `transactions` via ledger replay instead.
CREATE TABLE holdings (
    holding_id           TEXT PRIMARY KEY,
    portfolio_id         TEXT NOT NULL REFERENCES portfolios (portfolio_id),
    ticker               TEXT NOT NULL REFERENCES securities (ticker),
    quantity             REAL NOT NULL CHECK (quantity >= 0),
    cost_basis_per_share REAL NOT NULL CHECK (cost_basis_per_share >= 0),
    UNIQUE (portfolio_id, ticker)
);

CREATE TABLE transactions (
    transaction_id TEXT PRIMARY KEY,
    holding_id     TEXT NOT NULL REFERENCES holdings (holding_id),
    type           TEXT NOT NULL CHECK (type IN ('BUY', 'SELL')),
    quantity       REAL NOT NULL CHECK (quantity > 0),
    price          REAL NOT NULL CHECK (price >= 0),
    date           TEXT NOT NULL  -- ISO 8601 YYYY-MM-DD
);
CREATE INDEX idx_transactions_holding ON transactions (holding_id, date);

-- Daily total market value per portfolio (Task 3), loaded from backend/fixtures/performance-history.json.
CREATE TABLE performance_snapshots (
    portfolio_id TEXT NOT NULL REFERENCES portfolios (portfolio_id),
    date         TEXT NOT NULL,  -- ISO 8601 YYYY-MM-DD
    market_value REAL NOT NULL CHECK (market_value >= 0),
    PRIMARY KEY (portfolio_id, date)
);

CREATE TABLE exchange_rates (
    base_currency  TEXT NOT NULL,
    quote_currency TEXT NOT NULL,
    rate           REAL NOT NULL CHECK (rate > 0),
    PRIMARY KEY (base_currency, quote_currency)
);
