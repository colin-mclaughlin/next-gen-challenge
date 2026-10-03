"""Shared fixtures. HTTP tests run against the real mock CRM (node backend/mock-crm.mjs) on a random port."""
import json
import shutil
import socket
import subprocess
import time
from datetime import date, timedelta
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import DEFAULT_SEED_PATH, Settings
from app.db.database import MEMORY, build_database
from app.main import create_app

MOCK_CRM = Path(__file__).resolve().parents[2] / "mock-crm.mjs"
UNREACHABLE_CRM = "http://127.0.0.1:9"  # for apps whose tests never call the CRM
FIXED_TODAY = date(2026, 10, 3)  # history tests use a fixed "today" so they never depend on the real date


def write_history(path: Path, today: date = FIXED_TODAY) -> Path:
    """Same shape and formula as backend/fixtures/generate-history.mjs, ending on `today`."""
    fixtures = {}
    for portfolio_id, count, value in [("P-9001", 401, 48930), ("P-9002", 60, 500), ("P-EMPTY", 0, 0), ("P-SINGLE", 60, 2275)]:
        fixtures[portfolio_id] = [
            {
                "date": (today - timedelta(days=count - 1 - i)).isoformat(),
                "marketValue": round(value * (0.9 + 0.1 * (i + 1) / count), 2),
            }
            for i in range(count)
        ]
    path.write_text(json.dumps(fixtures), encoding="utf-8")
    return path


@pytest.fixture
def history_client(tmp_path):
    """App with seeded db + generated history ending FIXED_TODAY, and a clock pinned to that day."""
    conn = build_database(MEMORY, str(DEFAULT_SEED_PATH), str(write_history(tmp_path / "history.json")))
    app = create_app(Settings(crm_base_url=UNREACHABLE_CRM), db=conn, clock=lambda: FIXED_TODAY)
    with TestClient(app) as client:
        yield client
    conn.close()


@pytest.fixture
def db():
    """Fresh in-memory database with the schema and seed fixtures loaded."""
    conn = build_database(MEMORY, str(DEFAULT_SEED_PATH))
    yield conn
    conn.close()


@pytest.fixture
def app_client(db):
    """App backed by the seeded in-memory db; no mock CRM needed."""
    with TestClient(create_app(Settings(crm_base_url=UNREACHABLE_CRM), db=db)) as client:
        yield client


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class MockCrm:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def set_mode(self, mode: str) -> None:
        """Set the CRM's global failure mode: auto | ok | error | timeout | missing | nested."""
        httpx.post(f"{self.base_url}/__control", json={"mode": mode}).raise_for_status()

    def stats(self) -> dict:
        return httpx.get(f"{self.base_url}/__stats").json()


@pytest.fixture(scope="session")
def mock_crm():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required to run the mock CRM for HTTP tests.")
    port = _free_port()
    proc = subprocess.Popen([node, str(MOCK_CRM), f"--port={port}"], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    base_url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 10
        while True:
            try:
                if httpx.get(f"{base_url}/health", timeout=0.5).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            if proc.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError(f"Mock CRM failed to start: {proc.stderr.read().decode() if proc.stderr else ''}")
            time.sleep(0.1)
        yield MockCrm(base_url)
    finally:
        proc.terminate()
        proc.wait(timeout=5)
