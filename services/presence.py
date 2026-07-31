"""Presence Engine — orchestrates detection, scoring, and device lifecycle.

The central coordinator that connects detectors, confidence calculator,
device manager, and event bus into a cohesive presence detection pipeline.
"""

from __future__ import annotations

import structlog

from core.bus import AsyncioEventBus
from core.events import EventType
from core.types import EventPayload, MacAddress
from models.detection import DetectionResult
from models.device import Device
from models.enums import DetectionSource, DeviceStatus
from services.confidence import ConfidenceCalculator
from services.device_manager import DeviceManager

logger = structlog.get_logger(__name__)


class PresenceEngine:
    """Central presence detection engine.

    Listens for DEVICE_DETECTED events from all detectors, processes them
    through the confidence calculator, updates device state via the
    DeviceManager, and publishes DEVICE_ONLINE/OFFLINE/UPDATED events.

    Pipeline:
        Detector → DEVICE_DETECTED → ConfidenceCalculator → DeviceManager
            → DEVICE_ONLINE / DEVICE_OFFLINE / DEVICE_UPDATED
    """

    def __init__(
        self,
        bus: AsyncioEventBus,
        device_manager: DeviceManager,
        confidence: ConfidenceCalculator,
    ) -> None:
        """Initialize the PresenceEngine.

        Args:
            bus: Internal EventBus.
            device_manager: DeviceManager for device persistence.
            confidence: ConfidenceCalculator for scoring.
        """
        self._bus = bus
        self._device_manager = device_manager
        self._confidence = confidence

    def subscribe(self) -> None:
        """Subscribe to relevant events on the EventBus."""
        self._bus.subscribe(EventType.DEVICE_DETECTED, self._on_device_detected)
        logger.info("presence_engine_subscribed")

    async def _on_device_detected(self, payload: EventPayload) -> None:
        """Handle a DEVICE_DETECTED event from any detector.

        Processes the detection through the confidence pipeline:
        1. Parse detection data
        2. Calculate/update confidence score
        3. Get or create device via DeviceManager
        4. Update device state
        5. Publish appropriate events (ONLINE/OFFLINE/UPDATED)

        Args:
            payload: Detection event payload.
        """
        mac_raw = str(payload.get("mac", ""))
        ip = str(payload.get("ip", ""))
        hostname = str(payload.get("hostname", ""))
        source_str = str(payload.get("source", "unknown"))
        vendor = str(payload.get("vendor", ""))
        confidence_raw = payload.get("confidence", 0)
        extra = payload.get("extra", {})

        # Determine source enum
        try:
            source = DetectionSource(source_str)
        except ValueError:
            source = DetectionSource.UNKNOWN

        # If we have IP but no MAC, try to find MAC from existing device by IP
        if not mac_raw and ip:
            existing = await self._device_manager.get_by_ip(ip)
            if existing:
                mac_raw = existing.mac
            else:
                # Generate a deterministic synthetic MAC from IP
                # Uses locally-administered range (02:xx:xx:xx:xx:xx)
                mac_raw = self._ip_to_synthetic_mac(ip)

        if not mac_raw:
            logger.debug("detection_skipped_no_identifier", source=str(source))
            return

        mac = MacAddress(mac_raw)

        # Process through confidence calculator
        score, status, changed = self._confidence.process_detection(
            mac=mac,
            source=source,
            ip=ip,
            hostname=hostname,
            vendor=vendor,
        )

        # Get or create device
        device = await self._device_manager.get_or_create(mac)
        device.touch(source)
        device.update_confidence(score)

        # Update device fields from detection
        if ip:
            device.ip = ip
        if hostname:
            device.hostname = hostname
        if vendor:
            device.vendor = vendor

        # Determine new status
        new_status = self._confidence.get_status(mac)
        old_status = device.status
        device.status = new_status

        # Persist
        await self._device_manager.save(device)

        # Publish events
        if changed or old_status != new_status:
            if new_status == DeviceStatus.ONLINE:
                device.mark_online(source)
                await self._bus.publish(
                    EventType.DEVICE_ONLINE,
                    device.to_dict(),
                )
                logger.info("device_online", mac=mac, hostname=hostname, source=str(source))
            else:
                device.mark_offline()
                await self._bus.publish(
                    EventType.DEVICE_OFFLINE,
                    device.to_dict(),
                )
                logger.info("device_offline", mac=mac, hostname=hostname)
        else:
            await self._bus.publish(
                EventType.DEVICE_UPDATED,
                device.to_dict(),
            )

    async def apply_decay_cycle(self) -> None:
        """Apply confidence decay to all tracked devices.

        Devices whose confidence drops below the online threshold
        are marked offline and DEVICE_OFFLINE events are published.
        """
        went_offline = self._confidence.apply_decay()

        for mac in went_offline:
            device = await self._device_manager.get(mac)
            if device and device.is_online:
                device.mark_offline()
                device.update_confidence(0)
                await self._device_manager.save(device)
                await self._bus.publish(EventType.DEVICE_OFFLINE, device.to_dict())
                logger.info("device_decayed", mac=mac)

        logger.debug("decay_cycle_complete", offline_count=len(went_offline))

    @staticmethod
    def _ip_to_synthetic_mac(ip: str) -> str:
        """Generate a deterministic synthetic MAC address from an IP.

        Uses the locally-administered bit (02:xx) to avoid collision
        with real hardware MACs. Format: 02:PH:xx:xx:xx:xx where
        xx octets are derived from the IP octets.

        Args:
            ip: IPv4 address string.

        Returns:
            Synthetic MAC address string.
        """
        parts = ip.split(".")
        if len(parts) != 4:
            return ""
        return f"02:50:{int(parts[0]):02X}:{int(parts[1]):02X}:{int(parts[2]):02X}:{int(parts[3]):02X}"
