"""Database engine and session management.

Provides the async SQLAlchemy engine, session factory, and initialization
utilities for SQLite with aiosqlite.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.models.base import Base

logger = structlog.get_logger(__name__)

# Module-level engine and session factory (initialized by init_database)
_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_database(database_url: str, echo: bool = False) -> None:
    """Initialize the database engine and create all tables.

    This should be called once at application startup.

    Args:
        database_url: SQLAlchemy async database URL (e.g., sqlite+aiosqlite:///./data/presencehub.db).
        echo: Whether to log SQL statements (debug mode).
    """
    global _engine, _session_factory

    logger.info("database_initializing", url=database_url.split(":///")[-1] if ":///" in database_url else database_url)

    _engine = create_async_engine(
        database_url,
        echo=echo,
        future=True,
        pool_pre_ping=True,
    )

    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create all tables (for development; use Alembic in production)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("database_initialized")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session.

    Yields an AsyncSession that is automatically closed after use.
    Intended for use with FastAPI dependency injection.

    Yields:
        An async SQLAlchemy session.

    Raises:
        RuntimeError: If the database has not been initialized.
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_database() -> None:
    """Close the database engine and release all connections.

    Should be called at application shutdown.
    """
    global _engine
    if _engine is not None:
        await _engine.dispose()
        logger.info("database_closed")
        _engine = None


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get the session factory.

    Returns:
        The async session factory.

    Raises:
        RuntimeError: If the database has not been initialized.
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _session_factory
