"""Detection result domain models.

Represents the output of a presence detector — a single detection event
that carries the source, confidence, and device information.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from core.types import ConfidenceValue, Hostname, IPv4Address, MacAddress
from models.enums import DetectionSource


@dataclass(kw_only=True, slots=True)
class DetectionResult:
    """Result of a single presence detection from a detector.

    Each detector publishes DetectionResult instances to the EventBus.
    The PresenceEngine consumes these and updates device state accordingly.

    Attributes:
        mac: Detected device MAC address.
        ip: Detected device IP address.
        hostname: Detected hostname (may be empty).
        source: Which detector produced this result.
        confidence: Confidence score contributed by this detection.
        timestamp: When the detection occurred.
        vendor: Manufacturer name (if known).
        extra: Additional detector-specific metadata.
    """

    mac: MacAddress
    ip: IPv4Address
    hostname: Hostname = field(default=Hostname(""))
    source: DetectionSource
    confidence: ConfidenceValue
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    vendor: str = ""
    extra: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialize to a dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "mac": self.mac,
            "ip": self.ip,
            "hostname": self.hostname,
            "source": str(self.source),
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "vendor": self.vendor,
            "extra": self.extra,
        }

    def __repr__(self) -> str:
        return (
            f"DetectionResult(mac={self.mac!r}, ip={self.ip!r}, "
            f"source={self.source!r}, confidence={self.confidence})"
        )
