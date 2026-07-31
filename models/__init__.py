"""Domain models layer.

Pure Python dataclasses representing the core business entities:
Device, DetectionResult, ConfidenceScore, and supporting enums.
"""

from models.detection import DetectionResult
from models.device import Device
from models.enums import DetectionSource, DeviceStatus, DeviceType, OperatingSystem
from models.score import SOURCE_POINTS, ConfidenceScore, get_source_points

__all__ = [
    "ConfidenceScore",
    "DetectionResult",
    "DetectionSource",
    "Device",
    "DeviceStatus",
    "DeviceType",
    "OperatingSystem",
    "SOURCE_POINTS",
    "get_source_points",
]
