"""MQTT payload schemas for PresenceHub.

Defines the JSON payload structures for presence publications
and Home Assistant MQTT Discovery messages.
"""

from __future__ import annotations

from typing import Any

from models.device import Device
from models.enums import DeviceType


def device_presence_payload(device: Device) -> dict[str, Any]:
    """Build the JSON payload for a device presence update.

    Published to: home/presence/<device_mac>

    Args:
        device: The Device domain entity.

    Returns:
        JSON-serializable dictionary.
    """
    return {
        "name": device.friendly_name or device.hostname or device.mac,
        "online": device.is_online,
        "hostname": device.hostname,
        "ip": device.ip,
        "mac": device.mac,
        "vendor": device.vendor,
        "confidence": device.confidence,
        "last_seen": device.last_seen.isoformat(),
        "last_source": str(device.last_source),
        "device_type": str(device.device_type),
        "os_type": str(device.os_type),
    }


def online_payload(device: Device) -> str:
    """Build the simple online/offline payload.

    Published to: home/presence/<device_mac>/status

    Args:
        device: The Device domain entity.

    Returns:
        'online' or 'offline' string.
    """
    return "online" if device.is_online else "offline"


def ha_binary_sensor_discovery(
    device: Device,
    topic_prefix: str,
    discovery_prefix: str,
) -> tuple[str, dict[str, Any]]:
    """Build Home Assistant MQTT Discovery config for a binary_sensor.

    Creates an auto-discovered presence sensor in Home Assistant.

    Args:
        device: The Device domain entity.
        topic_prefix: MQTT topic prefix (e.g., 'home/presence').
        discovery_prefix: HA discovery prefix (e.g., 'homeassistant').

    Returns:
        Tuple of (discovery_topic, discovery_payload).
    """
    device_id = device.mac.replace(":", "_").lower()
    sensor_id = f"presence_{device_id}"

    discovery_topic = (
        f"{discovery_prefix}/binary_sensor/{sensor_id}/config"
    )

    payload: dict[str, Any] = {
        "name": device.friendly_name or device.hostname or f"Device {device.mac}",
        "unique_id": f"presencehub_{sensor_id}",
        "device_class": "presence",
        "state_topic": f"{topic_prefix}/{device_id}/status",
        "json_attributes_topic": f"{topic_prefix}/{device_id}/json",
        "payload_on": "online",
        "payload_off": "offline",
        "availability_topic": f"{topic_prefix}/status",
        "icon": _get_device_icon(device.device_type),
        "device": {
            "identifiers": [f"presencehub_{device_id}"],
            "name": device.friendly_name or device.hostname or device.mac,
            "manufacturer": device.vendor or "PresenceHub",
            "model": str(device.device_type),
            "suggested_area": _get_suggested_area(device.device_type),
        },
    }

    return discovery_topic, payload


def ha_device_tracker_discovery(
    device: Device,
    topic_prefix: str,
    discovery_prefix: str,
) -> tuple[str, dict[str, Any]]:
    """Build Home Assistant MQTT Discovery config for a device_tracker.

    Creates an auto-discovered device tracker in Home Assistant.

    Args:
        device: The Device domain entity.
        topic_prefix: MQTT topic prefix.
        discovery_prefix: HA discovery prefix.

    Returns:
        Tuple of (discovery_topic, discovery_payload).
    """
    device_id = device.mac.replace(":", "_").lower()
    tracker_id = f"tracker_{device_id}"

    discovery_topic = (
        f"{discovery_prefix}/device_tracker/{tracker_id}/config"
    )

    payload: dict[str, Any] = {
        "name": device.friendly_name or device.hostname or f"Device {device.mac}",
        "unique_id": f"presencehub_tracker_{device_id}",
        "state_topic": f"{topic_prefix}/{device_id}/status",
        "json_attributes_topic": f"{topic_prefix}/{device_id}/json",
        "payload_home": "online",
        "payload_not_home": "offline",
        "source_type": "router",
        "icon": "mdi:map-marker",
        "device": {
            "identifiers": [f"presencehub_{device_id}"],
            "name": device.friendly_name or device.hostname or device.mac,
            "manufacturer": device.vendor or "PresenceHub",
            "model": str(device.device_type),
            "suggested_area": _get_suggested_area(device.device_type),
        },
    }

    return discovery_topic, payload


def _get_device_icon(device_type: DeviceType) -> str:
    """Get a Material Design Icon for a device type.

    Args:
        device_type: The device type enum value.

    Returns:
        MDI icon string.
    """
    icons: dict[DeviceType, str] = {
        DeviceType.PHONE: "mdi:cellphone",
        DeviceType.TABLET: "mdi:tablet",
        DeviceType.LAPTOP: "mdi:laptop",
        DeviceType.DESKTOP: "mdi:desktop-tower",
        DeviceType.TV: "mdi:television",
        DeviceType.IOT: "mdi:chip",
        DeviceType.ROUTER: "mdi:router-network",
        DeviceType.SWITCH: "mdi:switch",
        DeviceType.ACCESS_POINT: "mdi:access-point",
        DeviceType.PRINTER: "mdi:printer",
        DeviceType.CAMERA: "mdi:camera",
        DeviceType.SPEAKER: "mdi:speaker",
        DeviceType.SERVER: "mdi:server",
        DeviceType.NAS: "mdi:nas",
        DeviceType.WEARABLE: "mdi:watch",
        DeviceType.GAMING: "mdi:gamepad-variant",
        DeviceType.OTHER: "mdi:devices",
        DeviceType.UNKNOWN: "mdi:help-circle",
    }
    return icons.get(device_type, "mdi:devices")


def _get_suggested_area(device_type: DeviceType) -> str | None:
    """Suggest a Home Assistant area based on device type.

    Args:
        device_type: The device type enum value.

    Returns:
        Suggested area name or None.
    """
    areas: dict[DeviceType, str | None] = {
        DeviceType.PHONE: None,          # Mobile — no fixed area
        DeviceType.TABLET: None,         # Mobile
        DeviceType.LAPTOP: None,         # Mobile
        DeviceType.DESKTOP: "Office",
        DeviceType.TV: "Living Room",
        DeviceType.IOT: None,
        DeviceType.ROUTER: "Network",
        DeviceType.SWITCH: "Network",
        DeviceType.ACCESS_POINT: "Network",
        DeviceType.PRINTER: "Office",
        DeviceType.CAMERA: None,
        DeviceType.SPEAKER: "Living Room",
        DeviceType.SERVER: "Office",
        DeviceType.NAS: "Office",
        DeviceType.WEARABLE: None,
        DeviceType.GAMING: "Living Room",
        DeviceType.OTHER: None,
        DeviceType.UNKNOWN: None,
    }
    return areas.get(device_type)
