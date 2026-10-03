"""The SQLAlchemy models describe exactly the schema in schema.sql, and their relationships navigate correctly."""
import datetime
import sqlite3

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import SCHEMA_PATH
from app.models import Base, Client, Holding, Portfolio, PricePoint, Security, Transaction, TransactionType


def describe(conn: sqlite3.Connection) -> dict:
    """Table -> (columns as (name, not_null, pk_position), foreign keys as (column, table, column))."""
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    shape = {}
    for table in tables:
        columns = sorted((c[1], bool(c[3]), c[5]) for c in conn.execute(f"PRAGMA table_info({table})"))
        fks = sorted((fk[3], fk[2], fk[4]) for fk in conn.execute(f"PRAGMA foreign_key_list({table})"))
        shape[table] = (columns, fks)
    return shape


@pytest.fixture
def engine():
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record):
        dbapi_connection.execute("PRAGMA foreign_keys = ON")

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def test_models_match_schema_sql_exactly(engine):
    from_sql = sqlite3.connect(":memory:")
    from_sql.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    with engine.connect() as conn:
        from_models = describe(conn.connection.driver_connection)
    assert from_models == describe(from_sql)


def test_relationships_navigate_between_objects(engine):
    with Session(engine) as session:
        client = Client(client_id="c1", name="Jane Doe")
        security = Security(ticker="AAPL", name="Apple Inc.", asset_class="Equity", price=227.5, previous_close_price=225)
        portfolio = Portfolio(portfolio_id="P-1", client=client, label="Brokerage", currency="CAD")
        holding = Holding(holding_id="h1", portfolio=portfolio, security=security, quantity=120, cost_basis_per_share=200)
        holding.transactions = [
            Transaction(transaction_id="t2", type=TransactionType.SELL, quantity=30, price=230, date=datetime.date(2025, 2, 1)),
            Transaction(transaction_id="t1", type=TransactionType.BUY, quantity=150, price=200, date=datetime.date(2025, 1, 2)),
        ]
        security.price_history = [PricePoint(date=datetime.date(2025, 1, 2), price=200)]
        session.add(client)
        session.commit()

    with Session(engine) as session:
        client = session.get(Client, "c1")
        assert [p.portfolio_id for p in client.portfolios] == ["P-1"]
        holding = client.portfolios[0].holdings[0]
        assert holding.security.name == "Apple Inc."
        assert [t.transaction_id for t in holding.transactions] == ["t1", "t2"]  # ordered by date
        assert holding.transactions[0].type is TransactionType.BUY
        assert session.get(Security, "AAPL").holdings[0].portfolio.client.name == "Jane Doe"


@pytest.mark.parametrize(
    "bad_row",
    [
        lambda: Portfolio(portfolio_id="P-X", client_id="no-such-client", label="x", currency="CAD"),  # foreign key
        lambda: Portfolio(portfolio_id="P-X", client_id="c1", label="x", currency="DOLLARS"),  # currency check
        lambda: Security(ticker="X", name="x", asset_class="Equity", price=-1, previous_close_price=1),  # price check
    ],
)
def test_database_rejects_invalid_rows(engine, bad_row):
    with Session(engine) as session:
        session.add(Client(client_id="c1", name="Jane"))
        session.commit()
        session.add(bad_row())
        with pytest.raises(IntegrityError):
            session.commit()
