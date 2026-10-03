"""Application factory. Dependencies are built here so tests can pass in their own settings/clients/db/clock."""
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.clock import Clock, utc_today
from app.config import DEFAULT_HISTORY_PATH, Settings, load_settings
from app.db.database import build_database
from app.db.history_fixture import ensure_history_file
from app.errors import register_error_handlers
from app.routers import history, holdings, portfolios
from app.services.crm_client import CrmClient
from app.services.history import HistoryService
from app.services.holdings import HoldingsService
from app.services.portfolio_metadata import PortfolioMetadataService


def create_app(
    settings: Settings | None = None,
    crm: CrmClient | None = None,
    db: sqlite3.Connection | None = None,
    clock: Clock = utc_today,
) -> FastAPI:
    settings = settings or load_settings()
    owns_crm, owns_db = crm is None, db is None
    crm_client = crm or CrmClient(settings.crm_base_url, settings.crm_timeout_seconds)
    conn = db or _build_default_database(settings, clock)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        # Only close what this factory created; injected dependencies belong to the caller.
        if owns_crm:
            await crm_client.aclose()
        if owns_db:
            conn.close()

    app = FastAPI(title="Portfolio Dashboard Backend", lifespan=lifespan)
    app.state.settings = settings
    app.state.portfolio_metadata = PortfolioMetadataService(crm_client)
    app.state.holdings = HoldingsService(conn)
    app.state.history = HistoryService(conn, clock)

    register_error_handlers(app)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(portfolios.router)
    app.include_router(holdings.router)
    app.include_router(history.router)
    return app


def _build_default_database(settings: Settings, clock: Clock) -> sqlite3.Connection:
    history_path = Path(settings.history_path)
    # The supplied generator only writes to its default location, so only refresh that file.
    if history_path.resolve() == DEFAULT_HISTORY_PATH.resolve():
        ensure_history_file(history_path, clock())
    return build_database(settings.database_path, settings.seed_path, settings.history_path)
