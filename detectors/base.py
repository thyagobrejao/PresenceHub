"""Base detector implementation providing common lifecycle management.

All concrete detectors (ARP, mDNS, Ping, DHCP) inherit from this class,
which implements the PresenceDetector interface with standardized
start/stop/health-check logic.
"""

from __future__ import annotations

import asyncio
from abc import abstractmethod
from typing import Any

import structlog

from config.loader import ConfigLoader
from core.bus import AsyncioEventBus
from core.events import EventType
from core.interfaces import PresenceDetector
from core.types import EventPayload


class BaseDetector(PresenceDetector):
    """Abstract base class for all presence detectors.

    Provides:
        - Standardized async start/stop with task management
        - Health check via task status
        - Event publishing helpers
        - Configurable scan interval
        - Structured logging with detector name context

    Subclasses must implement:
        - _scan_impl(): The actual detection logic
        - name property: Detector name string
    """

    def __init__(
        self,
        config: ConfigLoader,
        bus: AsyncioEventBus,
        interval: int | None = None,
    ) -> None:
        """Initialize the base detector.

        Args:
            config: Application configuration loader.
            bus: Internal EventBus for publishing detection results.
            interval: Scan interval in seconds. Falls back to detector config.
        """
        self._config = config
        self._bus = bus
        self._interval = interval or self._get_default_interval()
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._log = structlog.get_logger(__name__).bind(detector=self.name)

    @property
    def is_running(self) -> bool:
        """Whether the detector is currently active."""
        return self._running and (self._task is not None and not self._task.done())

    def _get_default_interval(self) -> int:
        """Get the default scan interval from configuration.

        Returns:
            Scan interval in seconds.
        """
        return self._config.get("detectors", self.name, "interval", default=60)

    async def start(self) -> None:
        """Start the detection loop.

        Creates a background task that runs _scan_loop periodically.
        Publishes a DETECTOR_STARTED event on the bus.
        """
        if self._running:
            self._log.warning("detector_already_running")
            return

        self._running = True
        self._task = asyncio.create_task(self._scan_loop(), name=f"detector-{self.name}")
        self._log.info("detector_started", interval=self._interval)
        await self._bus.publish(EventType.DETECTOR_STARTED, {"detector": self.name})

    async def stop(self) -> None:
        """Stop the detection loop gracefully.

        Cancels the background task and publishes a DETECTOR_STOPPED event.
        """
        if not self._running:
            return

        self._running = False

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self._log.info("detector_stopped")
        await self._bus.publish(EventType.DETECTOR_STOPPED, {"detector": self.name})

    async def health_check(self) -> bool:
        """Check whether the detector is healthy.

        Returns:
            True if the detector task is running, False otherwise.
        """
        if not self._running:
            return False
        if self._task is None:
            return False
        if self._task.done():
            exc = self._task.exception()
            if exc:
                self._log.error("detector_task_failed", error=str(exc))
            return False
        return True

    async def _scan_loop(self) -> None:
        """Main detection loop: runs _scan_impl at the configured interval.

        Handles errors gracefully — a single scan failure does not stop the loop.
        """
        while self._running:
            try:
                await self._scan_impl()
            except asyncio.CancelledError:
                break
            except Exception:
                self._log.exception("scan_error")
                await self._bus.publish(
                    EventType.DETECTOR_ERROR,
                    {"detector": self.name, "error": "scan_failed"},
                )

            # Sleep between scans, respecting shutdown
            try:
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                break

        self._log.info("scan_loop_exited")

    @abstractmethod
    async def _scan_impl(self) -> None:
        """Execute a single detection scan.

        Subclasses implement the actual detection logic here.
        Results should be published to the EventBus via self._bus.publish().
        """
        ...

    async def _publish_detections(
        self,
        detections: list[dict[str, Any]],
        source: str,
        confidence: int,
    ) -> None:
        """Publish a batch of detection results to the EventBus.

        Args:
            detections: List of detection dicts with 'mac', 'ip', 'hostname', 'vendor'.
            source: Detection source identifier.
            confidence: Confidence score contributed by this source.
        """
        published_count = 0
        for det in detections:
            mac = det.get("mac", "")
            ip = det.get("ip", "")
            # Allow detections without MAC (mDNS, Ping) — they will be
            # cross-referenced with ARP/DHCP to enrich the MAC later.
            if not mac and not ip:
                continue

            payload: EventPayload = {
                "mac": mac,
                "ip": ip,
                "hostname": det.get("hostname", ""),
                "source": source,
                "confidence": confidence,
                "vendor": det.get("vendor", ""),
                "extra": det.get("extra", {}),
            }

            await self._bus.publish(EventType.DEVICE_DETECTED, payload)
            published_count += 1

        if published_count:
            self._log.debug("detections_published", count=published_count, source=source)
