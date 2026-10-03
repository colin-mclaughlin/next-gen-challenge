"""Application factory. Dependencies are built here so tests can pass in their own settings/clients/db."""
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, load_settings
from app.db.database import build_database
from app.errors import register_error_handlers
from app.routers import holdings, portfolios
from app.services.crm_client import CrmClient
from app.services.holdings import HoldingsService
from app.services.portfolio_metadata import PortfolioMetadataService


def create_app(
    settings: Settings | None = None,
    crm: CrmClient | None = None,
    db: sqlite3.Connection | None = None,
) -> FastAPI:
    settings = settings or load_settings()
    owns_crm, owns_db = crm is None, db is None
    crm_client = crm or CrmClient(settings.crm_base_url, settings.crm_timeout_seconds)
    conn = db or build_database(settings.database_path, settings.seed_path)

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

    register_error_handlers(app)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(portfolios.router)
    app.include_router(holdings.router)
    return app
