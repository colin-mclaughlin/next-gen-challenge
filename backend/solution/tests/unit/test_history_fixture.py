import json
from datetime import date

import pytest

from app.config import DEFAULT_SEED_PATH
from app.db.database import MEMORY, SeedError, build_database
from app.db.history_fixture import ensure_history_file, latest_date
from conftest import FIXED_TODAY, write_history


class Recorder:
    def __init__(self, error: Exception | None = None):
        self.calls = 0
        self.error = error

    def __call__(self) -> None:
        self.calls += 1
        if self.error:
            raise self.error


def test_latest_date(tmp_path):
    assert latest_date(write_history(tmp_path / "h.json")) == FIXED_TODAY
    assert latest_date(tmp_path / "missing.json") is None
    (tmp_path / "bad.json").write_text("not json", encoding="utf-8")
    assert latest_date(tmp_path / "bad.json") is None


def test_fresh_file_is_not_regenerated(tmp_path):
    generate = Recorder()
    ensure_history_file(write_history(tmp_path / "h.json"), FIXED_TODAY, generate)
    assert generate.calls == 0


@pytest.mark.parametrize("state", ["missing", "stale"])
def test_missing_or_stale_file_is_regenerated(tmp_path, state):
    path = tmp_path / "h.json"
    if state == "stale":
        write_history(path, today=date(2026, 9, 1))
    generate = Recorder()
    ensure_history_file(path, FIXED_TODAY, generate)
    assert generate.calls == 1


def test_generator_failure_warns_instead_of_crashing(tmp_path, caplog):
    ensure_history_file(tmp_path / "h.json", FIXED_TODAY, Recorder(RuntimeError("Node.js is not on PATH.")))
    assert "could not be regenerated" in caplog.text


def test_history_is_loaded_into_the_database(tmp_path):
    engine = build_database(MEMORY, str(DEFAULT_SEED_PATH), str(write_history(tmp_path / "h.json")))
    with engine.connect() as conn:
        rows = conn.exec_driver_sql("SELECT portfolio_id, COUNT(*) FROM performance_snapshots GROUP BY portfolio_id")
        assert {portfolio_id: count for portfolio_id, count in rows} == {"P-9001": 401, "P-9002": 60, "P-SINGLE": 60}
    engine.dispose()


def test_missing_history_file_loads_no_history(tmp_path):
    engine = build_database(MEMORY, str(DEFAULT_SEED_PATH), str(tmp_path / "missing.json"))
    with engine.connect() as conn:
        assert conn.exec_driver_sql("SELECT COUNT(*) FROM performance_snapshots").scalar() == 0
    engine.dispose()


def test_history_for_unknown_portfolio_fails_loudly(tmp_path):
    path = tmp_path / "h.json"
    path.write_text(json.dumps({"P-GHOST": [{"date": "2026-10-03", "marketValue": 1}]}), encoding="utf-8")
    with pytest.raises(SeedError, match="P-GHOST"):
        build_database(MEMORY, str(DEFAULT_SEED_PATH), str(path))
