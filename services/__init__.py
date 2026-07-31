"""Services layer — business logic and orchestration."""

from services.confidence import ConfidenceCalculator
from services.device_manager import DeviceManager
from services.presence import PresenceEngine

__all__ = [
    "ConfidenceCalculator",
    "DeviceManager",
    "PresenceEngine",
]
