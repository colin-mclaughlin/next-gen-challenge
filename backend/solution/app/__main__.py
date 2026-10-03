"""`python -m app` starts the server using HOST/PORT from the environment."""
import uvicorn

from app.config import load_settings

if __name__ == "__main__":
    settings = load_settings()
    print(
        f"Portfolio backend: http://{settings.host}:{settings.port} "
        f"(CRM: {settings.crm_base_url}, timeout {settings.crm_timeout_seconds}s, DB: {settings.database_path})"
    )
    # factory=True: the app (and its database) is built when the server starts, not on import.
    uvicorn.run("app.main:create_app", factory=True, host=settings.host, port=settings.port)
