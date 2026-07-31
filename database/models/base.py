"""SQLAlchemy declarative base for PresenceHub database models.

All ORM models inherit from this base class.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy ORM models."""

    pass
