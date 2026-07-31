"""MQTT module for PresenceHub.

Provides async MQTT client with auto-reconnect, device presence publishing,
and Home Assistant MQTT Discovery integration.
"""

from mqtt.client import MqttClient
from mqtt.discovery import HADiscovery
from mqtt.publisher import MqttPublisher
from mqtt.schemas import (
    device_presence_payload,
    ha_binary_sensor_discovery,
    ha_device_tracker_discovery,
    online_payload,
)

__all__ = [
    "HADiscovery",
    "MqttClient",
    "MqttPublisher",
    "device_presence_payload",
    "ha_binary_sensor_discovery",
    "ha_device_tracker_discovery",
    "online_payload",
]
