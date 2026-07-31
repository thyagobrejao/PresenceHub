"""Detection event ORM model — persists detection history.

Every detection event from any source is recorded here for audit, history, and analytics.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base


class DetectionEventModel(Base):
    """SQLAlchemy ORM model for the 'detection_events' table.

    Records every individual detection event with source, confidence, and device info.
    """

    __tablename__ = "detection_events"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # noqa: A003

    # Device reference
    mac: Mapped[str] = mapped_column(String(17), index=True, comment="Device MAC address")
    ip: Mapped[str] = mapped_column(String(15), default="", comment="Detected IP address")
    hostname: Mapped[str] = mapped_column(String(255), default="", comment="Detected hostname")

    # Detection metadata
    source: Mapped[str] = mapped_column(String(50), index=True, comment="Detection source (arp, mdns, ping, etc.)")
    confidence: Mapped[int] = mapped_column(Integer, default=0, comment="Confidence contributed by this detection")
    vendor: Mapped[str] = mapped_column(String(255), default="", comment="Manufacturer from OUI lookup")

    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        comment="Detection timestamp (UTC)",
    )

    # Extra metadata (JSON string)
    extra_json: Mapped[str] = mapped_column(Text, default="{}", comment="Extra metadata as JSON string")

    def to_dict(self) -> dict[str, Any]:
        """Convert the ORM model to a dictionary."""
        return {
            "id": self.id,
            "mac": self.mac,
            "ip": self.ip,
            "hostname": self.hostname,
            "source": self.source,
            "confidence": self.confidence,
            "vendor": self.vendor,
            "timestamp": self.timestamp.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<DetectionEventModel(id={self.id}, mac={self.mac!r}, source={self.source!r})>"
