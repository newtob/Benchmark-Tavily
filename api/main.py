"""FastAPI application entry point for Benchmark Tavily."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict

from api.routers import benchmark_router
from api.services import load_fixtures, load_searches

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    app_name: str = "Benchmark Tavily"
    app_version: str = "0.1.0"

    tavily_api_key: str = ""


app_state: dict[str, object] = {
    "fixtures": {},
    "searches": [],
}

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Manage application startup and shutdown.

    On startup:
    - Load searches from searches.yaml
    - Load fixtures from api/fixtures/
    - Log warnings if fixtures are missing (don't fail)
    """
    del app
    logger.info("Starting Benchmark Tavily API")

    try:
        searches = load_searches()
        app_state["searches"] = searches
        logger.info(f"Loaded {len(searches)} searches")
    except FileNotFoundError as e:
        logger.error(f"Failed to load searches: {e}")
        logger.error("API will not function properly without searches.yaml")

    try:
        fixtures = load_fixtures()
        app_state["fixtures"] = fixtures
        if not fixtures:
            logger.warning(
                "No fixtures loaded. Benchmark results will be empty. "
                "Ensure api/fixtures/*.json files exist or tests will mock them."
            )
    except Exception as e:
        logger.error(f"Failed to load fixtures: {e}")
        logger.warning("Fixtures unavailable. This is expected in development/tests.")

    logger.info("API startup complete")
    yield

    logger.info("Shutting down Benchmark Tavily API")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(benchmark_router)


@app.get("/health")
@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint.

    Exposed at both /health (direct container probe) and /api/health
    (the path nginx and CI proxy to the FastAPI backend).

    Returns:
        Dictionary indicating server status.
    """
    return {"status": "ok", "service": settings.app_name}


@app.get("/ready")
@app.get("/api/ready")
async def readiness_check() -> dict[str, bool]:
    """Readiness check endpoint.

    Verifies that required data (searches and fixtures) are loaded.

    Returns:
        Dictionary indicating readiness status and which components are ready.
    """
    searches: Any = app_state.get("searches", [])
    fixtures: Any = app_state.get("fixtures", {})
    searches_ready = len(searches or []) > 0
    fixtures_ready = len(fixtures or {}) > 0

    return {
        "ready": searches_ready and fixtures_ready,
        "searches_loaded": searches_ready,
        "fixtures_loaded": fixtures_ready,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
    )
