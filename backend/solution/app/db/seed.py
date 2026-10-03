"""Load the fixture files into the database as model objects.

seed.json             -> clients, portfolios, securities (+ price history), holdings, transactions, rates
performance-history.json -> performance snapshots
"""
import datetime
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Client,
    ExchangeRate,
    Holding,
    PerformanceSnapshot,
    Portfolio,
    PricePoint,
    Security,
    Transaction,
    TransactionType,
)


class SeedError(ValueError):
    """The fixture data is inconsistent and cannot be loaded."""


def seed_database(session: Session, seed_path: str) -> None:
    data = json.loads(Path(seed_path).read_text(encoding="utf-8"))
    holdings = data.get("holdings", [])
    details = data.get("holdingDetails", [])

    session.add_all(Client(client_id=c["clientId"], name=c["name"]) for c in data.get("clients", []))
    session.add_all(
        Portfolio(portfolio_id=p["portfolioId"], client_id=p["clientId"], label=p["label"], currency=p["currency"])
        for p in data.get("portfolios", [])
    )
    session.add_all(_build_securities(holdings, details))
    session.add_all(
        PricePoint(ticker=d["ticker"], date=datetime.date.fromisoformat(point["date"]), price=point["price"])
        for d in details
        for point in d.get("priceHistory", [])
    )
    session.add_all(
        Holding(
            holding_id=h["holdingId"],
            portfolio_id=h["portfolioId"],
            ticker=h["ticker"],
            quantity=h["quantity"],
            cost_basis_per_share=h["costBasisPerShare"],
        )
        for h in holdings
    )
    session.add_all(
        Transaction(
            transaction_id=t["transactionId"],
            holding_id=t["holdingId"],
            type=TransactionType(t["type"]),
            quantity=t["quantity"],
            price=t["price"],
            date=datetime.date.fromisoformat(t["date"]),
        )
        for t in data.get("transactions", [])
    )
    if "CADtoUSD" in data:
        session.add(ExchangeRate(base_currency="CAD", quote_currency="USD", rate=data["CADtoUSD"]))
    # Send the inserts now (SQLAlchemy orders them so parents exist before children),
    # so constraint violations surface here rather than at some later commit.
    session.flush()


def load_history(session: Session, history_path: str) -> None:
    """Load `{ portfolioId: [{ date, marketValue }, ...] }` into performance snapshots."""
    data = json.loads(Path(history_path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SeedError(f"{history_path} must be an object keyed by portfolio id.")
    known = set(session.scalars(select(Portfolio.portfolio_id)))
    unknown = sorted(set(data) - known)
    if unknown:
        raise SeedError(f"{history_path} has history for unknown portfolios: {', '.join(unknown)}.")
    session.add_all(
        PerformanceSnapshot(
            portfolio_id=portfolio_id,
            date=datetime.date.fromisoformat(point["date"]),
            market_value=point["marketValue"],
        )
        for portfolio_id, points in data.items()
        for point in points
    )
    session.flush()


def _build_securities(holdings: list[dict[str, Any]], details: list[dict[str, Any]]) -> list[Security]:
    """Merge the security master: descriptive fields from holdingDetails, prices from holdings.

    In the seed, price/previousClosePrice live on each holding row. A security's price is a single
    market fact, so two holdings of the same ticker that disagree mean the fixture is wrong.
    """
    prices: dict[str, tuple[float, float]] = {}
    for holding in holdings:
        ticker = holding["ticker"]
        quote = (holding["price"], holding["previousClosePrice"])
        if ticker in prices and prices[ticker] != quote:
            raise SeedError(f"Holdings disagree on the price of {ticker}: {prices[ticker]} vs {quote}.")
        prices.setdefault(ticker, quote)

    by_ticker: dict[str, dict[str, Any]] = {}
    for holding in holdings:  # fallback descriptive fields for tickers without a detail record
        by_ticker.setdefault(holding["ticker"], {"name": holding["name"], "assetClass": holding["assetClass"]})
    for detail in details:
        by_ticker[detail["ticker"]] = {**by_ticker.get(detail["ticker"], {}), **detail}

    securities = []
    for ticker, info in by_ticker.items():
        if ticker not in prices:
            raise SeedError(f"No price available for {ticker}; it is not held by any portfolio.")
        price, previous_close = prices[ticker]
        securities.append(
            Security(
                ticker=ticker,
                name=info["name"],
                asset_class=info["assetClass"],
                sector=info.get("sector"),
                dividend_yield=info.get("dividendYield"),
                fifty_two_week_low=info.get("fiftyTwoWeekLow"),
                fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
                price=price,
                previous_close_price=previous_close,
            )
        )
    return securities
