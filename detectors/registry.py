"""Detector registry — manages detector discovery and lifecycle.

Provides a central registry for all PresenceDetector instances.
Supports dynamic loading of detectors based on configuration.
"""

from __future__ import annotations

from typing import Any

import structlog

from config.loader import ConfigLoader
from core.bus import AsyncioEventBus
from core.interfaces import PresenceDetector
from detectors.arp.detector import ArpDetector
from detectors.dhcp.detector import DhcpDetector
from detectors.mdns.detector import MdnsDetector
from detectors.ping.detector import PingDetector

logger = structlog.get_logger(__name__)

# Map of detector names to their factory functions
_DETECTOR_FACTORIES: dict[str, type[PresenceDetector]] = {
    "arp": ArpDetector,
    "mdns": MdnsDetector,
    "ping": PingDetector,
    "dhcp": DhcpDetector,
}


class DetectorRegistry:
    """Manages detector instances and their lifecycle.

    Loads enabled detectors from configuration, instantiates them,
    and provides start/stop/health-check for all registered detectors.
    """

    def __init__(self, config: ConfigLoader, bus: AsyncioEventBus) -> None:
        """Initialize the registry.

        Args:
            config: Application configuration.
            bus: Internal EventBus instance.
        """
        self._config = config
        self._bus = bus
        self._detectors: dict[str, PresenceDetector] = {}

    @property
    def detectors(self) -> dict[str, PresenceDetector]:
        """Get all registered detector instances."""
        return self._detectors.copy()

    def load_enabled(self) -> None:
        """Load and instantiate all enabled detectors from configuration.

        Only detectors with 'enabled: true' in config are loaded.
        """
        for name, factory in _DETECTOR_FACTORIES.items():
            enabled = self._config.get("detectors", name, "enabled", default=False)
            if not enabled:
                logger.info("detector_disabled", detector=name)
                continue

            try:
                detector = factory(self._config, self._bus)
                self._detectors[name] = detector
                logger.info("detector_loaded", detector=name)
            except Exception:
                logger.exception("detector_load_failed", detector=name)

        logger.info("detectors_loaded", count=len(self._detectors), names=list(self._detectors.keys()))

    def get(self, name: str) -> PresenceDetector | None:
        """Get a detector by name.

        Args:
            name: Detector name (e.g., 'arp', 'mdns').

        Returns:
            The detector instance, or None if not found.
        """
        return self._detectors.get(name)

    async def start_all(self) -> None:
        """Start all registered detectors.

        Detectors are started concurrently. Failures in one do not
        prevent others from starting.
        """
        import asyncio

        tasks = []
        for name, detector in self._detectors.items():
            tasks.append(self._safe_start(name, detector))

        if tasks:
            await asyncio.gather(*tasks)

        logger.info("all_detectors_started", count=len(self._detectors))

    async def stop_all(self) -> None:
        """Stop all registered detectors gracefully.

        Detectors are stopped concurrently with a timeout.
        """
        import asyncio

        tasks = []
        for name, detector in self._detectors.items():
            tasks.append(self._safe_stop(name, detector))

        if tasks:
            await asyncio.gather(*tasks)

        self._detectors.clear()
        logger.info("all_detectors_stopped")

    async def health_check_all(self) -> dict[str, bool]:
        """Check health of all detectors.

        Returns:
            Dictionary mapping detector names to their health status.
        """
        results: dict[str, bool] = {}
        for name, detector in self._detectors.items():
            try:
                results[name] = await detector.health_check()
            except Exception:
                results[name] = False
        return results

    async def _safe_start(self, name: str, detector: PresenceDetector) -> None:
        """Start a detector, catching and logging errors.

        Args:
            name: Detector name.
            detector: Detector instance.
        """
        try:
            await detector.start()
        except Exception:
            logger.exception("detector_start_failed", detector=name)

    async def _safe_stop(self, name: str, detector: PresenceDetector) -> None:
        """Stop a detector, catching and logging errors.

        Args:
            name: Detector name.
            detector: Detector instance.
        """
        try:
            await detector.stop()
        except Exception:
            logger.exception("detector_stop_failed", detector=name)

    def register_factory(self, name: str, factory: type[PresenceDetector]) -> None:
        """Register a custom detector factory.

        Allows external plugins or future detectors to be registered at runtime.

        Args:
            name: Detector name.
            factory: Detector class (must implement PresenceDetector).
        """
        _DETECTOR_FACTORIES[name] = factory
        logger.info("detector_factory_registered", detector=name)
