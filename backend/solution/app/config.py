"""Runtime configuration from environment variables, with defaults for local development."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 3000
    crm_base_url: str = "http://localhost:4002"
    crm_timeout_seconds: float = 2.0


def load_settings(env: dict[str, str] | None = None) -> Settings:
    env = os.environ if env is None else env
    return Settings(
        host=env.get("HOST", "127.0.0.1"),
        port=_int_in_range("PORT", env.get("PORT", "3000"), 0, 65535),
        crm_base_url=env.get("CRM_BASE_URL", "http://localhost:4002"),
        crm_timeout_seconds=_int_in_range("CRM_TIMEOUT_MS", env.get("CRM_TIMEOUT_MS", "2000"), 1, 600_000) / 1000,
    )


def _int_in_range(name: str, raw: str, low: int, high: int) -> int:
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f'{name} must be an integer, got "{raw}".') from None
    if not low <= value <= high:
        raise ValueError(f'{name} must be between {low} and {high}, got {value}.')
    return value
