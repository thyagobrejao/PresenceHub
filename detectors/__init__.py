"""Detectors layer for PresenceHub.

Each detector is a self-contained module implementing the PresenceDetector
interface. The DetectorRegistry manages their lifecycle.

Available detectors:
    - ArpDetector: System ARP table scanning
    - MdnsDetector: mDNS/Bonjour service discovery
    - PingDetector: ICMP echo requests
    - DhcpDetector: DHCP lease file parsing
"""

from detectors.base import BaseDetector
from detectors.registry import DetectorRegistry

__all__ = [
    "BaseDetector",
    "DetectorRegistry",
]
