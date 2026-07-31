"""Database layer for PresenceHub.

Provides async SQLAlchemy engine, session management, ORM models,
repositories, and Alembic migration support.
"""

from database.engine import close_database, get_session, get_session_factory, init_database
from database.models import Base, DetectionEventModel, DeviceModel, SettingModel

__all__ = [
    "Base",
    "DetectionEventModel",
    "DeviceModel",
    "SettingModel",
    "close_database",
    "get_session",
    "get_session_factory",
    "init_database",
]
