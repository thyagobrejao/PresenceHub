"""Domain exception hierarchy for PresenceHub.

All domain-level exceptions inherit from PresenceHubError,
enabling consistent error handling across the system.
"""


class PresenceHubError(Exception):
    """Base exception for all PresenceHub domain errors."""


# --- Device Errors ---

class DeviceError(PresenceHubError):
    """Base exception for device-related errors."""


class DeviceNotFoundError(DeviceError):
    """Raised when a device is not found in the repository."""

    def __init__(self, mac: str) -> None:
        self.mac = mac
        super().__init__(f"Device not found: {mac}")


class DeviceAlreadyExistsError(DeviceError):
    """Raised when attempting to create a device that already exists."""

    def __init__(self, mac: str) -> None:
        self.mac = mac
        super().__init__(f"Device already exists: {mac}")


# --- Detection Errors ---

class DetectionError(PresenceHubError):
    """Base exception for detection-related errors."""


class DetectorStartError(DetectionError):
    """Raised when a detector fails to start."""

    def __init__(self, detector_name: str, reason: str) -> None:
        self.detector_name = detector_name
        self.reason = reason
        super().__init__(f"Detector '{detector_name}' failed to start: {reason}")


class DetectorStopError(DetectionError):
    """Raised when a detector fails to stop."""

    def __init__(self, detector_name: str, reason: str) -> None:
        self.detector_name = detector_name
        self.reason = reason
        super().__init__(f"Detector '{detector_name}' failed to stop: {reason}")


# --- Configuration Errors ---

class ConfigurationError(PresenceHubError):
    """Base exception for configuration-related errors."""


class InvalidConfigurationError(ConfigurationError):
    """Raised when the configuration is invalid or missing required fields."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Invalid configuration: {message}")


# --- MQTT Errors ---

class MqttError(PresenceHubError):
    """Base exception for MQTT-related errors."""


class MqttConnectionError(MqttError):
    """Raised when the MQTT client fails to connect."""

    def __init__(self, host: str, port: int, reason: str) -> None:
        self.host = host
        self.port = port
        self.reason = reason
        super().__init__(f"MQTT connection to {host}:{port} failed: {reason}")


class MqttPublishError(MqttError):
    """Raised when publishing to MQTT fails."""

    def __init__(self, topic: str, reason: str) -> None:
        self.topic = topic
        self.reason = reason
        super().__init__(f"MQTT publish to '{topic}' failed: {reason}")


# --- Event Bus Errors ---

class EventBusError(PresenceHubError):
    """Base exception for event bus errors."""


class EventHandlerError(EventBusError):
    """Raised when an event handler throws an exception."""

    def __init__(self, event_type: str, reason: str) -> None:
        self.event_type = event_type
        self.reason = reason
        super().__init__(f"Event handler for '{event_type}' failed: {reason}")
