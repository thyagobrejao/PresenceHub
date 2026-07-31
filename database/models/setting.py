"""Settings ORM model — persists user-configurable settings to the database.

Allows runtime settings to be stored and modified via the API.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base


class SettingModel(Base):
    """SQLAlchemy ORM model for the 'settings' table.

    Stores key-value settings that can be modified at runtime.
    """

    __tablename__ = "settings"

    # Primary key
    key: Mapped[str] = mapped_column(String(255), primary_key=True, comment="Setting key")

    # Value
    value: Mapped[str] = mapped_column(Text, default="", comment="Setting value (stored as string)")

    # Metadata
    description: Mapped[str] = mapped_column(String(500), default="", comment="Setting description")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Last update timestamp (UTC)",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert the ORM model to a dictionary."""
        return {
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "updated_at": self.updated_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<SettingModel(key={self.key!r}, value={self.value!r})>"
