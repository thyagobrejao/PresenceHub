"""Core layer of PresenceHub — domain primitives, interfaces, and the EventBus.

All core types, abstract interfaces, domain events, and the internal EventBus
live here. This layer has zero external dependencies beyond the Python standard
library and structlog.
"""

from core.bus import AsyncioEventBus
from core.events import EventType
from core.exceptions import (
    ConfigurationError,
    DetectionError,
    DeviceAlreadyExistsError,
    DeviceError,
    DeviceNotFoundError,
    DetectorStartError,
    DetectorStopError,
    EventBusError,
    EventHandlerError,
    InvalidConfigurationError,
    MqttConnectionError,
    MqttError,
    MqttPublishError,
    PresenceHubError,
)
from core.interfaces import EventBus, EventHandler, PresenceDetector, Repository
from core.types import (
    ConfidenceValue,
    DeviceId,
    EventPayload,
    Hostname,
    IPv4Address,
    JsonDict,
    MacAddress,
    normalize_mac,
)

__all__ = [
    # Bus
    "AsyncioEventBus",
    # Events
    "EventType",
    # Exceptions
    "ConfigurationError",
    "DetectionError",
    "DeviceAlreadyExistsError",
    "DeviceError",
    "DeviceNotFoundError",
    "DetectorStartError",
    "DetectorStopError",
    "EventBusError",
    "EventHandlerError",
    "InvalidConfigurationError",
    "MqttConnectionError",
    "MqttError",
    "MqttPublishError",
    "PresenceHubError",
    # Interfaces
    "EventBus",
    "EventHandler",
    "PresenceDetector",
    "Repository",
    # Types
    "ConfidenceValue",
    "DeviceId",
    "EventPayload",
    "Hostname",
    "IPv4Address",
    "JsonDict",
    "MacAddress",
    "normalize_mac",
]
