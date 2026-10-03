"""Runtime configuration from environment variables, with defaults for local development."""
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

SOLUTION_DIR = Path(__file__).resolve().parents[1]  # backend/solution
DEFAULT_DATABASE_PATH = SOLUTION_DIR / "data" / "app.db"
DEFAULT_SEED_PATH = SOLUTION_DIR.parent / "fixtures" / "seed.json"  # backend/fixtures/seed.json


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 3000
    crm_base_url: str = "http://localhost:4002"
    crm_timeout_seconds: float = 2.0
    database_path: str = str(DEFAULT_DATABASE_PATH)  # ":memory:" for tests
    seed_path: str = str(DEFAULT_SEED_PATH)


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    source: Mapping[str, str] = os.environ if env is None else env
    return Settings(
        host=source.get("HOST", "127.0.0.1"),
        port=_int_in_range("PORT", source.get("PORT", "3000"), 0, 65535),
        crm_base_url=source.get("CRM_BASE_URL", "http://localhost:4002"),
        crm_timeout_seconds=_int_in_range("CRM_TIMEOUT_MS", source.get("CRM_TIMEOUT_MS", "2000"), 1, 600_000) / 1000,
        database_path=source.get("DATABASE_PATH", str(DEFAULT_DATABASE_PATH)),
        seed_path=source.get("SEED_PATH", str(DEFAULT_SEED_PATH)),
    )


def _int_in_range(name: str, raw: str, low: int, high: int) -> int:
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f'{name} must be an integer, got "{raw}".') from None
    if not low <= value <= high:
        raise ValueError(f'{name} must be between {low} and {high}, got {value}.')
    return value
