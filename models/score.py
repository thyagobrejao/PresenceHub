"""Confidence score domain model.

Implements the scoring logic that determines device online/offline status
based on cumulative confidence from multiple detection sources.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from core.types import ConfidenceValue, MacAddress
from models.enums import DetectionSource

# Confidence points contributed by each detection source
SOURCE_POINTS: dict[DetectionSource, int] = {
    DetectionSource.ARP: 100,
    DetectionSource.MDNS: 90,
    DetectionSource.DHCP: 80,
    DetectionSource.MQTT: 70,
    DetectionSource.HA_COMPANION: 70,
    DetectionSource.PING: 60,
    DetectionSource.BLUETOOTH: 60,
    DetectionSource.ESPHOME: 65,
    DetectionSource.SNMP: 50,
    DetectionSource.UNIFI: 75,
    DetectionSource.TPLINK: 75,
    DetectionSource.MANUAL: 100,
    DetectionSource.UNKNOWN: 10,
}


def get_source_points(source: DetectionSource) -> int:
    """Get the confidence points contributed by a detection source.

    Args:
        source: The detection source.

    Returns:
        Points contributed by this source (0-100).
    """
    return SOURCE_POINTS.get(source, 10)


@dataclass(kw_only=True, slots=True)
class ConfidenceScore:
    """Tracks and calculates the confidence score for a device.

    The score is the sum of points from all detection sources that have
    recently detected the device. It decays over time when detections stop.

    Attributes:
        mac: Associated device MAC address.
        score: Current aggregated confidence score (0-100).
        sources: Set of detection sources that contributed.
        last_calculated: When the score was last updated.
    """

    mac: MacAddress
    score: ConfidenceValue = ConfidenceValue(0)
    sources: set[DetectionSource] = field(default_factory=set)
    last_calculated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_source(self, source: DetectionSource) -> None:
        """Add a detection source and recalculate the score.

        Args:
            source: The detection source to add.
        """
        self.sources.add(source)
        self._recalculate()

    def remove_source(self, source: DetectionSource) -> None:
        """Remove a detection source and recalculate.

        Args:
            source: The detection source to remove.
        """
        self.sources.discard(source)
        self._recalculate()

    def _recalculate(self) -> None:
        """Recalculate the confidence score as sum of source points, capped at 100."""
        total = sum(SOURCE_POINTS.get(s, 10) for s in self.sources)
        self.score = ConfidenceValue(min(100, total))
        self.last_calculated = datetime.now(timezone.utc)

    def decay(self, rate: int = 5) -> ConfidenceValue:
        """Apply decay to the confidence score.

        Reduces the score by the given rate, clearing all sources when
        the score reaches zero.

        Args:
            rate: Points to subtract per decay cycle.

        Returns:
            The new confidence score after decay.
        """
        if self.score <= 0:
            self.sources.clear()
            return ConfidenceValue(0)

        self.score = ConfidenceValue(max(0, self.score - rate))

        if self.score <= 0:
            self.sources.clear()

        self.last_calculated = datetime.now(timezone.utc)
        return self.score

    def reset(self) -> None:
        """Reset the confidence score to zero."""
        self.score = ConfidenceValue(0)
        self.sources.clear()
        self.last_calculated = datetime.now(timezone.utc)

    @property
    def is_online(self) -> bool:
        """Whether the device is considered online based on its score."""
        return self.score > 0

    def to_dict(self) -> dict[str, object]:
        """Serialize to dictionary."""
        return {
            "mac": self.mac,
            "score": self.score,
            "sources": [str(s) for s in self.sources],
            "last_calculated": self.last_calculated.isoformat(),
        }
