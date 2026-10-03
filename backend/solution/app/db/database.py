"""SQLite setup: open a connection, create the schema, and seed it from backend/fixtures/seed.json.

The database is a disposable copy of the fixtures: `build_database` deletes and rebuilds it on
every start, so every run (and every test) begins from the same known state.
"""
import json
import sqlite3
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
MEMORY = ":memory:"


class SeedError(ValueError):
    """The fixture data is inconsistent and cannot be loaded."""


def open_database(path: str) -> sqlite3.Connection:
    if path != MEMORY:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: the connection is created at startup and used from async routes
    # on the event-loop thread (see docs/task-02.md, "Threading").
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def build_database(path: str, seed_path: str, history_path: str | None = None) -> sqlite3.Connection:
    """Delete any existing database file, then create the schema and load the fixtures.

    `history_path` is optional: when it is None or the file doesn't exist, no performance
    history is loaded (history endpoints return []).
    """
    if path != MEMORY:
        for suffix in ("", "-journal", "-wal", "-shm"):
            Path(path + suffix).unlink(missing_ok=True)
    conn = open_database(path)
    init_schema(conn)
    seed_from_fixtures(conn, seed_path)
    if history_path is not None and Path(history_path).exists():
        load_history(conn, history_path)
    return conn


def load_history(conn: sqlite3.Connection, history_path: str) -> None:
    """Load `{ portfolioId: [{ date, marketValue }, ...] }` into performance_snapshots."""
    data = json.loads(Path(history_path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SeedError(f"{history_path} must be an object keyed by portfolio id.")
    known = {row[0] for row in conn.execute("SELECT portfolio_id FROM portfolios")}
    unknown = sorted(set(data) - known)
    if unknown:
        raise SeedError(f"{history_path} has history for unknown portfolios: {', '.join(unknown)}.")
    rows = [(portfolio_id, point["date"], point["marketValue"]) for portfolio_id, points in data.items() for point in points]
    with conn:
        conn.executemany("INSERT INTO performance_snapshots (portfolio_id, date, market_value) VALUES (?, ?, ?)", rows)


def seed_from_fixtures(conn: sqlite3.Connection, seed_path: str) -> None:
    data = json.loads(Path(seed_path).read_text(encoding="utf-8"))
    securities = _build_securities(data.get("holdings", []), data.get("holdingDetails", []))

    with conn:  # one transaction: all or nothing
        conn.executemany("INSERT INTO clients (client_id, name) VALUES (:clientId, :name)", data.get("clients", []))
        conn.executemany(
            "INSERT INTO portfolios (portfolio_id, client_id, label, currency) "
            "VALUES (:portfolioId, :clientId, :label, :currency)",
            data.get("portfolios", []),
        )
        conn.executemany(
            "INSERT INTO securities (ticker, name, asset_class, sector, dividend_yield, fifty_two_week_low, "
            "fifty_two_week_high, price, previous_close_price) VALUES (:ticker, :name, :assetClass, :sector, "
            ":dividendYield, :fiftyTwoWeekLow, :fiftyTwoWeekHigh, :price, :previousClosePrice)",
            securities,
        )
        conn.executemany(
            "INSERT INTO security_price_history (ticker, date, price) VALUES (?, ?, ?)",
            [
                (detail["ticker"], point["date"], point["price"])
                for detail in data.get("holdingDetails", [])
                for point in detail.get("priceHistory", [])
            ],
        )
        conn.executemany(
            "INSERT INTO holdings (holding_id, portfolio_id, ticker, quantity, cost_basis_per_share) "
            "VALUES (:holdingId, :portfolioId, :ticker, :quantity, :costBasisPerShare)",
            data.get("holdings", []),
        )
        conn.executemany(
            "INSERT INTO transactions (transaction_id, holding_id, type, quantity, price, date) "
            "VALUES (:transactionId, :holdingId, :type, :quantity, :price, :date)",
            data.get("transactions", []),
        )
        if "CADtoUSD" in data:
            conn.execute(
                "INSERT INTO exchange_rates (base_currency, quote_currency, rate) VALUES ('CAD', 'USD', ?)",
                (data["CADtoUSD"],),
            )


def _build_securities(holdings: list[dict[str, Any]], details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge the security master: descriptive fields from holdingDetails, prices from holdings.

    In the seed, price/previousClosePrice live on each holding row. A security's price is a single
    market fact, so two holdings of the same ticker that disagree mean the fixture is wrong.
    """
    prices: dict[str, dict[str, Any]] = {}
    for holding in holdings:
        ticker = holding["ticker"]
        quote = {"price": holding["price"], "previousClosePrice": holding["previousClosePrice"]}
        if ticker in prices and prices[ticker] != quote:
            raise SeedError(f"Holdings disagree on the price of {ticker}: {prices[ticker]} vs {quote}.")
        prices.setdefault(ticker, quote)

    by_ticker: dict[str, dict[str, Any]] = {}
    for holding in holdings:  # fallback descriptive fields for tickers without a detail record
        by_ticker.setdefault(
            holding["ticker"],
            {"ticker": holding["ticker"], "name": holding["name"], "assetClass": holding["assetClass"]},
        )
    for detail in details:
        by_ticker[detail["ticker"]] = {**by_ticker.get(detail["ticker"], {}), **detail}

    securities = []
    for ticker, security in by_ticker.items():
        if ticker not in prices:
            raise SeedError(f"No price available for {ticker}; it is not held by any portfolio.")
        securities.append(
            {
                "sector": None,
                "dividendYield": None,
                "fiftyTwoWeekLow": None,
                "fiftyTwoWeekHigh": None,
                **security,
                **prices[ticker],
            }
        )
    return securities
