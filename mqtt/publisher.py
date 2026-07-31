"""MQTT Device Presence Publisher.

Listens to device events on the internal EventBus and publishes
presence updates to MQTT topics for Home Assistant consumption.
"""

from __future__ import annotations

import structlog

from core.bus import AsyncioEventBus
from core.events import EventType
from core.types import EventPayload, JsonDict
from models.device import Device
from mqtt.client import MqttClient
from mqtt.schemas import device_presence_payload, online_payload

logger = structlog.get_logger(__name__)


class MqttPublisher:
    """Publishes device presence to MQTT topics.

    Subscribes to DEVICE_ONLINE/OFFLINE/UPDATED events on the EventBus
    and publishes corresponding MQTT messages.

    Topics published:
        home/presence/<mac>/status   — "online" | "offline"
        home/presence/<mac>/json     — full JSON payload
    """

    def __init__(self, client: MqttClient, bus: AsyncioEventBus) -> None:
        """Initialize the publisher.

        Args:
            client: MQTT client instance.
            bus: Internal EventBus for subscribing to device events.
        """
        self._client = client
        self._bus = bus

    def subscribe(self) -> None:
        """Subscribe to relevant device events on the EventBus."""
        self._bus.subscribe(EventType.DEVICE_ONLINE, self._on_device_online)
        self._bus.subscribe(EventType.DEVICE_OFFLINE, self._on_device_offline)
        self._bus.subscribe(EventType.DEVICE_UPDATED, self._on_device_updated)
        self._bus.subscribe(EventType.DEVICE_DETECTED, self._on_device_detected)
        logger.info("mqtt_publisher_subscribed")

    async def publish_device(self, device: Device) -> None:
        """Publish full device presence to MQTT.

        Args:
            device: The Device entity to publish.
        """
        if not self._client.is_connected:
            return

        prefix = self._client.topic_prefix
        mac_topic = device.mac.replace(":", "_").lower()

        # Publish simple status
        try:
            await self._client.publish(
                f"{prefix}/{mac_topic}/status",
                online_payload(device),
                qos=1,
                retain=False,
            )
        except Exception:
            logger.exception("mqtt_publish_status_failed", mac=device.mac)

        # Publish full JSON
        try:
            await self._client.publish(
                f"{prefix}/{mac_topic}/json",
                device_presence_payload(device),
                qos=1,
                retain=False,
            )
        except Exception:
            logger.exception("mqtt_publish_json_failed", mac=device.mac)

        logger.debug("mqtt_device_published", mac=device.mac, online=device.is_online)

    async def _on_device_online(self, payload: EventPayload) -> None:
        """Handle DEVICE_ONLINE event — publish online status."""
        device = self._payload_to_device(payload)
        if device:
            await self.publish_device(device)

    async def _on_device_offline(self, payload: EventPayload) -> None:
        """Handle DEVICE_OFFLINE event — publish offline status."""
        device = self._payload_to_device(payload)
        if device:
            await self.publish_device(device)

    async def _on_device_updated(self, payload: EventPayload) -> None:
        """Handle DEVICE_UPDATED event — publish updated device."""
        device = self._payload_to_device(payload)
        if device:
            await self.publish_device(device)

    async def _on_device_detected(self, payload: EventPayload) -> None:
        """Handle DEVICE_DETECTED event — publish detected device.

        This publishes immediately when a new device is first seen,
        even before full processing by the PresenceEngine.
        """
        mac = str(payload.get("mac", ""))
        ip = str(payload.get("ip", ""))
        hostname = str(payload.get("hostname", ""))

        if not mac and not ip:
            return

        # Build a minimal device object for immediate publishing
        device = Device(
            mac=mac or "unknown",
            ip=ip or "",
            hostname=hostname or "",
        )

        try:
            await self.publish_device(device)
        except Exception:
            logger.exception("mqtt_publish_detected_failed")

    @staticmethod
    def _payload_to_device(payload: EventPayload) -> Device | None:
        """Convert an EventPayload to a Device if possible.

        Args:
            payload: Event payload dictionary.

        Returns:
            Device instance or None if insufficient data.
        """
        mac = str(payload.get("mac", ""))
        if not mac:
            return None

        return Device(
            mac=mac,
            ip=str(payload.get("ip", "")),
            hostname=str(payload.get("hostname", "")),
            vendor=str(payload.get("vendor", "")),
            confidence=int(payload.get("confidence", 0)),
        )
