"""FastAPI dependency injection.

Provides reusable dependencies for database sessions, config access,
and other shared resources.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from fastapi import Request

from sqlalchemy.ext.asyncio import AsyncSession

from config.loader import ConfigLoader
from database.engine import get_session
from database.repositories.device import DeviceRepository
from database.repositories.event import EventRepository


async def get_device_repo() -> AsyncGenerator[DeviceRepository, None]:
    """Dependency that provides a DeviceRepository with an active session.

    Yields:
        DeviceRepository instance.
    """
    async for session in get_session():
        yield DeviceRepository(session)


async def get_event_repo() -> AsyncGenerator[EventRepository, None]:
    """Dependency that provides an EventRepository with an active session.

    Yields:
        EventRepository instance.
    """
    async for session in get_session():
        yield EventRepository(session)


def get_config() -> ConfigLoader:
    """Dependency that provides the application ConfigLoader.

    Returns:
        The global ConfigLoader instance.

    Raises:
        RuntimeError: If config hasn't been loaded.
    """
    from api.app import _app_config

    if _app_config is None:
        raise RuntimeError("Configuration not loaded. Call create_app() first.")
    return _app_config


def get_device_manager(request: Request) -> Any:
    """Dependency that provides the active DeviceManager instance."""
    return getattr(request.app.state, "device_manager", None)


def get_event_bus(request: Request) -> Any:
    """Dependency that provides the active EventBus instance."""
    return getattr(request.app.state, "bus", None)
