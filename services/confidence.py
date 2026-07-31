"""Confidence Score Calculator.

Manages confidence scores for all tracked devices, applying
detection source points and periodic decay.
"""

from __future__ import annotations

from datetime import datetime, timezone

import structlog

from core.types import ConfidenceValue, MacAddress
from models.enums import DetectionSource, DeviceStatus
from models.score import SOURCE_POINTS, ConfidenceScore

logger = structlog.get_logger(__name__)


class ConfidenceCalculator:
    """Calculates and manages confidence scores for devices.

    Tracks which detection sources have seen each device and computes
    an aggregate confidence score. Applies decay to reduce scores
    when devices stop being detected.

    The confidence score is the sum of points from active detection
    sources, capped at 100. When a device hasn't been detected by
    a source within the timeout period, that source's points are removed.

    Online threshold: score >= threshold → ONLINE, otherwise → OFFLINE.
    """

    def __init__(
        self,
        online_threshold: int = 50,
        decay_rate: int = 5,
        default_ttl: int = 300,
    ) -> None:
        """Initialize the confidence calculator.

        Args:
            online_threshold: Minimum score to be considered online.
            decay_rate: Points subtracted per decay cycle.
            default_ttl: Default TTL in seconds for new devices.
        """
        self._scores: dict[MacAddress, ConfidenceScore] = {}
        self._online_threshold = online_threshold
        self._decay_rate = decay_rate
        self._default_ttl = default_ttl

    def process_detection(
        self,
        mac: MacAddress,
        source: DetectionSource,
        ip: str = "",
        hostname: str = "",
        vendor: str = "",
    ) -> tuple[ConfidenceValue, DeviceStatus, bool]:
        """Process a detection event for a device.

        Adds the source's confidence points and determines online/offline status.

        Args:
            mac: Device MAC address.
            source: Detection source.
            ip: Device IP (for logging).
            hostname: Device hostname.
            vendor: Device vendor.

        Returns:
            Tuple of (new_score, status, status_changed).
        """
        if mac not in self._scores:
            self._scores[mac] = ConfidenceScore(mac=mac)

        score = self._scores[mac]
        old_status = self._determine_status(score.score)
        score.add_source(source)
        new_status = self._determine_status(score.score)
        changed = old_status != new_status

        logger.debug(
            "confidence_updated",
            mac=mac,
            source=str(source),
            old_score=score.score - SOURCE_POINTS.get(source, 0),
            new_score=score.score,
            status=str(new_status),
            changed=changed,
        )

        return score.score, new_status, changed

    def get_score(self, mac: MacAddress) -> ConfidenceScore | None:
        """Get the confidence score for a device.

        Args:
            mac: Device MAC address.

        Returns:
            ConfidenceScore or None if the device is not tracked.
        """
        return self._scores.get(mac)

    def get_status(self, mac: MacAddress) -> DeviceStatus:
        """Get the online/offline status for a device.

        Args:
            mac: Device MAC address.

        Returns:
            DeviceStatus.ONLINE or DeviceStatus.OFFLINE.
        """
        score = self._scores.get(mac)
        if score is None:
            return DeviceStatus.OFFLINE
        return self._determine_status(score.score)

    def apply_decay(self) -> list[MacAddress]:
        """Apply decay to all tracked devices.

        Reduces each device's score by the decay rate.
        Devices that reach zero have their sources cleared.

        Returns:
            List of MAC addresses that transitioned to offline.
        """
        went_offline: list[MacAddress] = []

        for mac, score in list(self._scores.items()):
            was_online = self._determine_status(score.score) == DeviceStatus.ONLINE
            score.decay(self._decay_rate)
            is_online = self._determine_status(score.score) == DeviceStatus.ONLINE

            if was_online and not is_online:
                went_offline.append(mac)
                logger.info("device_decayed_offline", mac=mac, score=score.score)

            # Remove scores that have fully decayed and no sources
            if score.score <= 0 and not score.sources:
                del self._scores[mac]

        if went_offline:
            logger.info("decay_applied", offline_count=len(went_offline), total_tracked=len(self._scores))

        return went_offline

    def remove_device(self, mac: MacAddress) -> None:
        """Remove a device from confidence tracking.

        Args:
            mac: Device MAC address.
        """
        self._scores.pop(mac, None)
        logger.debug("confidence_removed", mac=mac)

    def _determine_status(self, score: ConfidenceValue) -> DeviceStatus:
        """Determine device status from confidence score.

        Args:
            score: Current confidence score.

        Returns:
            ONLINE if score >= threshold, OFFLINE otherwise.
        """
        return DeviceStatus.ONLINE if score >= self._online_threshold else DeviceStatus.OFFLINE

    @property
    def tracked_count(self) -> int:
        """Number of devices currently tracked."""
        return len(self._scores)

    @property
    def online_count(self) -> int:
        """Number of devices currently online."""
        return sum(1 for s in self._scores.values() if self._determine_status(s.score) == DeviceStatus.ONLINE)
