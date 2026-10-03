"""Application factory. Dependencies are built here so tests can pass in their own settings/clients."""
from fastapi import FastAPI

from app.config import Settings, load_settings
from app.errors import register_error_handlers
from app.routers import portfolios
from app.services.crm_client import CrmClient
from app.services.portfolio_metadata import PortfolioMetadataService


def create_app(settings: Settings | None = None, crm: CrmClient | None = None) -> FastAPI:
    settings = settings or load_settings()
    crm = crm or CrmClient(settings.crm_base_url, settings.crm_timeout_seconds)

    app = FastAPI(title="Portfolio Dashboard Backend")
    app.state.settings = settings
    app.state.portfolio_metadata = PortfolioMetadataService(crm)

    register_error_handlers(app)

    @app.get("/health", tags=["health"])
    async def health() -> dict:
        return {"status": "ok"}

    app.include_router(portfolios.router)
    return app


app = create_app()
