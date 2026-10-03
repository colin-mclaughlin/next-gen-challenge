"""Shared fixtures. HTTP tests run against the real mock CRM (node backend/mock-crm.mjs) on a random port."""
import shutil
import socket
import subprocess
import time
from pathlib import Path

import httpx
import pytest

MOCK_CRM = Path(__file__).resolve().parents[2] / "mock-crm.mjs"


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
