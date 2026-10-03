"""`python -m app` starts the server using HOST/PORT from the environment."""
import uvicorn

from app.config import load_settings

if __name__ == "__main__":
    settings = load_settings()
    print(f"Portfolio backend: http://{settings.host}:{settings.port} (CRM: {settings.crm_base_url}, timeout {settings.crm_timeout_seconds}s)")
    uvicorn.run("app.main:app", host=settings.host, port=settings.port)
