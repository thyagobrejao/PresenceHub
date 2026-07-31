"""Shared pytest fixtures for PresenceHub tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config.loader import ConfigLoader
from core.bus import AsyncioEventBus
from database.models.base import Base


@pytest.fixture
def event_bus() -> AsyncioEventBus:
    """Provide a fresh AsyncioEventBus instance."""
    return AsyncioEventBus()


@pytest.fixture
def config() -> ConfigLoader:
    """Provide a ConfigLoader with default configuration."""
    return ConfigLoader.load(None)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an in-memory SQLite database session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    await engine.dispose()
