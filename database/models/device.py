"""Device ORM model — SQLAlchemy mapping for the devices table.

Persists device state, history, and configuration to SQLite.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base


class DeviceModel(Base):
    """SQLAlchemy ORM model for the 'devices' table.

    Maps to the Device domain model with full persistence support.
    """

    __tablename__ = "devices"

    # Primary key
    mac: Mapped[str] = mapped_column(String(17), primary_key=True, comment="MAC address (AA:BB:CC:DD:EE:FF)")

    # Network identification
    hostname: Mapped[str] = mapped_column(String(255), default="", comment="Device hostname")
    ip: Mapped[str] = mapped_column(String(15), default="", comment="Last known IPv4 address")
    vendor: Mapped[str] = mapped_column(String(255), default="", comment="Manufacturer from OUI lookup")

    # Timestamps
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        comment="First detection timestamp (UTC)",
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        comment="Most recent detection timestamp (UTC)",
    )

    # Detection metadata
    last_source: Mapped[str] = mapped_column(String(50), default="unknown", comment="Most recent detection source")
    confidence: Mapped[int] = mapped_column(Integer, default=0, comment="Confidence score (0-100)")
    status: Mapped[str] = mapped_column(String(10), default="unknown", comment="Device status: online/offline/unknown")

    # User metadata
    friendly_name: Mapped[str] = mapped_column(String(255), default="", comment="User-assigned friendly name")
    description: Mapped[str] = mapped_column(Text, default="", comment="User-assigned description")
    device_type: Mapped[str] = mapped_column(String(50), default="unknown", comment="Device type classification")
    os_type: Mapped[str] = mapped_column(String(50), default="unknown", comment="Operating system")

    # Configuration
    ttl: Mapped[int] = mapped_column(Integer, default=300, comment="Time-to-live in seconds")

    # Extra metadata (JSON string)
    extra_json: Mapped[str] = mapped_column(Text, default="{}", comment="Extra metadata as JSON string")

    def to_dict(self) -> dict[str, Any]:
        """Convert the ORM model to a dictionary."""
        return {
            "mac": self.mac,
            "hostname": self.hostname,
            "ip": self.ip,
            "vendor": self.vendor,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "last_source": self.last_source,
            "confidence": self.confidence,
            "status": self.status,
            "friendly_name": self.friendly_name,
            "description": self.description,
            "device_type": self.device_type,
            "os_type": self.os_type,
            "ttl": self.ttl,
        }

    def __repr__(self) -> str:
        return f"<DeviceModel(mac={self.mac!r}, hostname={self.hostname!r}, status={self.status!r})>"
