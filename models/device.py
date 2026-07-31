"""Device domain model.

The Device is the central domain entity representing a detected network device.
It uses dataclasses for simplicity, immutability by default, and type safety.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from core.types import ConfidenceValue, DeviceId, Hostname, IPv4Address, MacAddress
from models.enums import DetectionSource, DeviceStatus, DeviceType, OperatingSystem


@dataclass(kw_only=True, slots=True)
class Device:
    """Represents a detected network device with presence tracking.

    Attributes:
        mac: Primary key — device MAC address.
        hostname: Device hostname (may be empty).
        ip: Last known IPv4 address.
        vendor: Manufacturer name derived from OUI lookup.
        first_seen: Timestamp of first detection.
        last_seen: Timestamp of most recent detection.
        last_source: Most recent detection source.
        confidence: Current confidence score (0-100).
        status: Online/offline status.
        friendly_name: User-assigned friendly name.
        description: User-assigned description.
        device_type: Device type classification.
        os_type: Operating system (when detectable).
        ttl: Time-to-live in seconds before considered offline.
        extra: Arbitrary extra metadata dict.
    """

    mac: MacAddress
    hostname: Hostname = field(default=Hostname(""))
    ip: IPv4Address = field(default=IPv4Address(""))
    vendor: str = ""

    first_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_source: DetectionSource = DetectionSource.UNKNOWN

    confidence: ConfidenceValue = ConfidenceValue(0)
    status: DeviceStatus = DeviceStatus.UNKNOWN

    friendly_name: str = ""
    description: str = ""
    device_type: DeviceType = DeviceType.UNKNOWN
    os_type: OperatingSystem = OperatingSystem.UNKNOWN

    ttl: int = 300

    extra: dict[str, str] = field(default_factory=dict)

    @property
    def id(self) -> DeviceId:  # noqa: A003
        """The device unique identifier (its MAC address)."""
        return DeviceId(self.mac)

    @property
    def is_online(self) -> bool:
        """Convenience property for online status check."""
        return self.status == DeviceStatus.ONLINE

    def touch(self, source: DetectionSource | None = None) -> None:
        """Update last_seen and optionally last_source.

        Args:
            source: The detection source that triggered this touch.
        """
        self.last_seen = datetime.now(timezone.utc)
        if source is not None:
            self.last_source = source

    def mark_online(self, source: DetectionSource | None = None) -> None:
        """Mark the device as online and update timestamps.

        Args:
            source: The detection source.
        """
        self.status = DeviceStatus.ONLINE
        self.touch(source)

    def mark_offline(self) -> None:
        """Mark the device as offline."""
        self.status = DeviceStatus.OFFLINE

    def update_confidence(self, value: ConfidenceValue) -> None:
        """Update the confidence score, clamped to 0-100.

        Args:
            value: New confidence value.
        """
        self.confidence = ConfidenceValue(max(0, min(100, value)))

    def to_dict(self) -> dict[str, object]:
        """Serialize the device to a JSON-compatible dictionary.

        Returns:
            Dictionary representation suitable for API responses and MQTT payloads.
        """
        return {
            "mac": self.mac,
            "hostname": self.hostname,
            "ip": self.ip,
            "vendor": self.vendor,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "last_source": str(self.last_source),
            "confidence": self.confidence,
            "status": str(self.status),
            "friendly_name": self.friendly_name,
            "description": self.description,
            "device_type": str(self.device_type),
            "os_type": str(self.os_type),
            "ttl": self.ttl,
            "extra": self.extra,
        }

    def __repr__(self) -> str:
        return (
            f"Device(mac={self.mac!r}, hostname={self.hostname!r}, "
            f"ip={self.ip!r}, status={self.status!r}, confidence={self.confidence})"
        )
