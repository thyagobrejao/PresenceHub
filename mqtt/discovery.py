"""Home Assistant MQTT Discovery integration.

Automatically creates binary_sensor and device_tracker entities in Home Assistant
via MQTT Discovery, requiring zero manual configuration.
"""

from __future__ import annotations

from typing import Any

import structlog

from core.bus import AsyncioEventBus
from core.events import EventType
from core.types import EventPayload
from models.device import Device
from mqtt.client import MqttClient
from mqtt.schemas import (
    ha_binary_sensor_discovery,
    ha_device_tracker_discovery,
)

logger = structlog.get_logger(__name__)


class HADiscovery:
    """Publishes Home Assistant MQTT Discovery configurations.

    When a new device is detected, this automatically publishes
    discovery messages so HA creates the corresponding entities
    without any manual YAML configuration.

    Entities created:
        - binary_sensor.presence_<mac>  (presence sensor)
        - device_tracker.tracker_<mac>  (device tracker)
    """

    def __init__(
        self,
        client: MqttClient,
        bus: AsyncioEventBus,
        device_manager: Any | None = None,
        discovery_prefix: str = "homeassistant",
    ) -> None:
        """Initialize HA Discovery.

        Args:
            client: MQTT client instance.
            bus: Internal EventBus.
            device_manager: Optional DeviceManager instance for looking up full device metadata.
            discovery_prefix: HA MQTT discovery prefix (default: homeassistant).
        """
        self._client = client
        self._bus = bus
        self._device_manager = device_manager
        self._discovery_prefix = discovery_prefix
        self._discovered: set[str] = set()

    def subscribe(self) -> None:
        """Subscribe to device events to trigger discovery."""
        self._bus.subscribe(EventType.DEVICE_DETECTED, self._on_device_detected)
        self._bus.subscribe(EventType.DEVICE_UPDATED, self._on_device_updated)
        self._bus.subscribe(EventType.MQTT_CONNECTED, self._on_mqtt_connected)
        logger.info("ha_discovery_subscribed")

    async def _on_mqtt_connected(self, payload: EventPayload) -> None:
        """Handle MQTT_CONNECTED event — publish discovery for all known devices."""
        if not self._device_manager:
            return

        devices = await self._device_manager.get_all()
        logger.info("ha_discovery_publishing_all", count=len(devices))
        for device in devices:
            await self.publish_discovery(device, force=True)

    async def publish_discovery(self, device: Device, force: bool = False) -> None:
        """Publish MQTT Discovery configs for a device.

        Creates binary_sensor and device_tracker discovery messages.

        Args:
            device: The Device entity to register in HA.
            force: Whether to force re-publishing even if already discovered.
        """
        if not force and device.mac in self._discovered:
            return

        if not self._client.is_connected:
            return

        prefix = self._client.topic_prefix

        # Binary sensor (presence)
        topic, payload = ha_binary_sensor_discovery(
            device, prefix, self._discovery_prefix
        )
        try:
            await self._client.publish(topic, payload, qos=1, retain=True)
            logger.debug("ha_discovery_binary_sensor", mac=device.mac)
        except Exception:
            logger.exception("ha_discovery_publish_failed", mac=device.mac, type="binary_sensor")

        # Device tracker
        topic, payload = ha_device_tracker_discovery(
            device, prefix, self._discovery_prefix
        )
        try:
            await self._client.publish(topic, payload, qos=1, retain=True)
            logger.debug("ha_discovery_device_tracker", mac=device.mac)
        except Exception:
            logger.exception("ha_discovery_publish_failed", mac=device.mac, type="device_tracker")

        self._discovered.add(device.mac)
        logger.info("ha_discovery_published", mac=device.mac, name=device.friendly_name or device.hostname)

    async def remove_discovery(self, mac: str) -> None:
        """Remove discovery entries for a device (publish empty config).

        Args:
            mac: Device MAC address.
        """
        device_id = mac.replace(":", "_").lower()
        prefix = self._client.topic_prefix
        dp = self._discovery_prefix

        # Clear binary sensor config
        try:
            await self._client.publish(
                f"{dp}/binary_sensor/presence_{device_id}/config",
                "",
                qos=1,
                retain=True,
            )
        except Exception:
            pass

        # Clear device tracker config
        try:
            await self._client.publish(
                f"{dp}/device_tracker/tracker_{device_id}/config",
                "",
                qos=1,
                retain=True,
            )
        except Exception:
            pass

        self._discovered.discard(mac)
        logger.info("ha_discovery_removed", mac=mac)

    async def _on_device_detected(self, payload: EventPayload) -> None:
        """Handle DEVICE_DETECTED event — publish discovery if new.

        Args:
            payload: Event payload with device data.
        """
        mac = str(payload.get("mac", ""))
        if not mac:
            return

        device: Device | None = None
        if self._device_manager:
            device = await self._device_manager.get(mac)

        if not device:
            device = Device(
                mac=mac,
                ip=str(payload.get("ip", "")),
                hostname=str(payload.get("hostname", "")),
                vendor=str(payload.get("vendor", "")),
                friendly_name=str(payload.get("friendly_name", "")),
            )

        await self.publish_discovery(device)

    async def _on_device_updated(self, payload: EventPayload) -> None:
        """Handle DEVICE_UPDATED event — re-publish discovery with updated metadata.

        Args:
            payload: Event payload with updated device data.
        """
        mac = str(payload.get("mac", ""))
        if not mac:
            return

        device: Device | None = None
        if self._device_manager:
            device = await self._device_manager.get(mac)

        if not device:
            device = Device(
                mac=mac,
                ip=str(payload.get("ip", "")),
                hostname=str(payload.get("hostname", "")),
                vendor=str(payload.get("vendor", "")),
                friendly_name=str(payload.get("friendly_name", "")),
            )

        await self.publish_discovery(device, force=True)
