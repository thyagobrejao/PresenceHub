"""PresenceHub server entry point.

Starts the Uvicorn ASGI server with the FastAPI application.
Run with: python -m api.server
"""

from __future__ import annotations

import uvicorn

from api.app import create_app
from config.loader import ConfigLoader
from database.engine import init_database
from utils.logging import configure_logging


def main() -> None:
    """Initialize and start the PresenceHub server."""
    # Load configuration
    config = ConfigLoader.load("config/config.yaml")

    # Configure structured logging
    log_level = config.get("logging", "level", default="INFO")
    json_format = config.get("logging", "json_format", default=True)
    configure_logging(level=log_level, json_format=json_format)

    import structlog

    logger = structlog.get_logger(__name__)

    # Initialize database
    import asyncio

    db_url = config.get("database", "url", default="sqlite+aiosqlite:///./data/presencehub.db")
    db_echo = config.get("database", "echo", default=False)
    asyncio.run(init_database(db_url, echo=db_echo))

    # Create FastAPI app
    app = create_app(config)

    # Get server settings
    host = config.get("api", "host", default="0.0.0.0")
    port = config.get("api", "port", default=8000)

    logger.info("server_starting", host=host, port=port)

    # Start Uvicorn
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level.lower(),
        access_log=True,
    )


if __name__ == "__main__":
    main()
