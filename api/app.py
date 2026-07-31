"""FastAPI application factory for PresenceHub.

Creates and configures the FastAPI application with all routes,
middleware, and lifecycle handlers.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from api.middleware import setup_middleware
from api.routes import (
    devices_router,
    health_router,
    history_router,
    metrics_router,
    stats_router,
)
from config.loader import ConfigLoader

# Module-level reference to the config (set during create_app)
_app_config: ConfigLoader | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:  # type: ignore[type-arg]
    """Application lifespan handler — startup and shutdown.

    Database is initialized externally; this handles any API-specific
    startup/shutdown needs.
    """
    import structlog

    logger = structlog.get_logger(__name__)
    logger.info("api_starting")

    yield

    logger.info("api_shutting_down")


def create_app(config: ConfigLoader | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        config: Application configuration loader.
                If None, a default config is loaded.

    Returns:
        Configured FastAPI application instance.
    """
    global _app_config

    if config is None:
        config = ConfigLoader.load("config/config.yaml")
    _app_config = config

    # Get API settings
    swagger_enabled = config.get("api", "swagger_enabled", default=True)
    cors_origins = config.get("api", "cors_origins", default=["*"])

    app = FastAPI(
        title="PresenceHub API",
        description="The best residential presence detection service for Home Assistant",
        version="0.1.0",
        docs_url="/docs" if swagger_enabled else None,
        redoc_url="/redoc" if swagger_enabled else None,
        openapi_url="/openapi.json" if swagger_enabled else None,
        lifespan=lifespan,
    )

    # Setup middleware
    setup_middleware(app, cors_origins)

    # Register routes
    app.include_router(devices_router)
    app.include_router(history_router)
    app.include_router(stats_router)
    app.include_router(health_router)
    app.include_router(metrics_router)

    return app
