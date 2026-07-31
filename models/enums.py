"""Domain enumerations for PresenceHub.

All shared enums are defined here to avoid circular imports and ensure
type safety across the system.
"""

from enum import StrEnum


class DeviceStatus(StrEnum):
    """Device online/offline status."""

    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class DetectionSource(StrEnum):
    """Source of a presence detection event."""

    ARP = "arp"
    MDNS = "mdns"
    PING = "ping"
    DHCP = "dhcp"
    MQTT = "mqtt"
    HA_COMPANION = "ha_companion"
    ESPHOME = "esphome"
    BLUETOOTH = "bluetooth"
    SNMP = "snmp"
    UNIFI = "unifi"
    TPLINK = "tplink"
    MANUAL = "manual"
    UNKNOWN = "unknown"


class DeviceType(StrEnum):
    """Type of detected device."""

    PHONE = "phone"
    TABLET = "tablet"
    LAPTOP = "laptop"
    DESKTOP = "desktop"
    TV = "tv"
    IOT = "iot"
    ROUTER = "router"
    SWITCH = "switch"
    ACCESS_POINT = "access_point"
    PRINTER = "printer"
    CAMERA = "camera"
    SPEAKER = "speaker"
    SERVER = "server"
    NAS = "nas"
    WEARABLE = "wearable"
    GAMING = "gaming"
    OTHER = "other"
    UNKNOWN = "unknown"


class OperatingSystem(StrEnum):
    """Device operating system (when detectable)."""

    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    IOS = "ios"
    ANDROID = "android"
    CHROMEOS = "chromeos"
    FREEBSD = "freebsd"
    EMBEDDED = "embedded"
    UNKNOWN = "unknown"
