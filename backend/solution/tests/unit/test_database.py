import json
import sqlite3

import pytest

from app.config import DEFAULT_SEED_PATH
from app.db import repositories
from app.db.database import MEMORY, SeedError, build_database


def count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_seed_loads_every_fixture_table(db):
    assert count(db, "clients") == 2
    assert count(db, "portfolios") == 4
    assert count(db, "holdings") == 5
    assert count(db, "securities") == 4  # AAPL held twice, stored once
    assert count(db, "transactions") == 8
    assert count(db, "security_price_history") == 4
    assert db.execute("SELECT rate FROM exchange_rates WHERE base_currency='CAD' AND quote_currency='USD'").fetchone()[0] == 0.73


def test_security_details_are_merged_with_prices(db):
    row = db.execute("SELECT * FROM securities WHERE ticker = 'AAPL'").fetchone()
    assert (row["sector"], row["dividend_yield"], row["price"], row["previous_close_price"]) == ("Technology", 0.005, 227.5, 225)
    assert db.execute("SELECT dividend_yield FROM securities WHERE ticker = 'ZERO'").fetchone()[0] is None


def test_foreign_keys_are_enforced(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO holdings VALUES ('hX', 'NO-SUCH-PORTFOLIO', 'AAPL', 1, 1)")


def test_check_constraints_reject_invalid_rows(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO transactions VALUES ('tX', 'h1', 'GIFT', 1, 1, '2025-01-01')")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO holdings VALUES ('hX', 'P-EMPTY', 'AAPL', -1, 1)")


def test_conflicting_prices_for_one_ticker_fail_loudly(tmp_path):
    seed = json.loads(DEFAULT_SEED_PATH.read_text(encoding="utf-8"))
    seed["holdings"][4]["price"] = 999  # second AAPL holding disagrees with the first
    bad_seed = tmp_path / "seed.json"
    bad_seed.write_text(json.dumps(seed), encoding="utf-8")
    with pytest.raises(SeedError, match="AAPL"):
        build_database(MEMORY, str(bad_seed))


def test_file_database_is_rebuilt_from_scratch(tmp_path):
    path = str(tmp_path / "app.db")
    first = build_database(path, str(DEFAULT_SEED_PATH))
    with first.begin() as conn:
        conn.exec_driver_sql("DELETE FROM transactions")
    first.dispose()
    second = build_database(path, str(DEFAULT_SEED_PATH))
    with second.connect() as conn:
        assert conn.exec_driver_sql("SELECT COUNT(*) FROM transactions").scalar() == 8
    second.dispose()


def test_repositories(db):
    assert repositories.portfolio_exists(db, "P-9001")
    assert not repositories.portfolio_exists(db, "UNKNOWN")
    assert [p.ticker for p in repositories.list_positions(db, "P-9001")] == ["AAPL", "BND", "ZERO"]
    assert repositories.list_positions(db, "P-EMPTY") == []
