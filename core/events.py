"""Domain event type constants for the PresenceHub system.

All event types are centralized here to ensure consistency and enable
compile-time validation of event type strings.
"""

from enum import StrEnum


class EventType(StrEnum):
    """Centralized registry of all domain event types."""

    # Device lifecycle events
    DEVICE_DETECTED = "device.detected"
    DEVICE_UPDATED = "device.updated"
    DEVICE_ONLINE = "device.online"
    DEVICE_OFFLINE = "device.offline"
    DEVICE_REMOVED = "device.removed"
    DEVICE_EXPIRED = "device.expired"

    # Detector events
    DETECTOR_STARTED = "detector.started"
    DETECTOR_STOPPED = "detector.stopped"
    DETECTOR_ERROR = "detector.error"
    DETECTOR_HEALTH = "detector.health"

    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_HEALTH = "system.health"

    # MQTT events
    MQTT_CONNECTED = "mqtt.connected"
    MQTT_DISCONNECTED = "mqtt.disconnected"
    MQTT_MESSAGE = "mqtt.message"

    # Confidence events
    CONFIDENCE_CHANGED = "confidence.changed"
    CONFIDENCE_DECAY = "confidence.decay"
