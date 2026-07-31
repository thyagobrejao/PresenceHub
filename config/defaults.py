"""Default configuration values for PresenceHub.

These defaults are merged with user-provided YAML configuration values.
Environment variables override these defaults.
"""

from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "mqtt": {
        "host": "localhost",
        "port": 1883,
        "username": "",
        "password": "",
        "client_id": "presencehub",
        "topic_prefix": "home/presence",
        "keepalive": 60,
        "reconnect_interval": 5,
        "reconnect_max_interval": 60,
        "qos": 1,
        "retain": False,
    },
    "network": {
        "interface": "eth0",
        "subnet": "192.168.1.0/24",
        "ping_timeout": 2,
        "ping_count": 1,
        "arp_scan_interval": 60,
        "mdns_scan_interval": 30,
        "dhcp_lease_paths": [
            "/var/lib/dhcp/dhcpd.leases",
            "/var/lib/misc/dnsmasq.leases",
            "/tmp/dhcp.leases",
        ],
    },
    "presence": {
        "timeout": 300,
        "decay_interval": 60,
        "decay_rate": 5,
        "online_threshold": 50,
        "stale_cleanup_interval": 600,
    },
    "detectors": {
        "arp": {"enabled": True, "interval": 60},
        "mdns": {"enabled": True, "interval": 30},
        "ping": {"enabled": True, "interval": 120},
        "dhcp": {"enabled": True, "interval": 60},
    },
    "api": {
        "host": "0.0.0.0",
        "port": 8000,
        "cors_origins": ["*"],
        "swagger_enabled": True,
    },
    "home_assistant": {
        "discovery_enabled": True,
        "discovery_prefix": "homeassistant",
    },
    "database": {
        "url": "sqlite+aiosqlite:///./data/presencehub.db",
        "echo": False,
    },
    "logging": {
        "level": "INFO",
        "json_format": True,
        "render_console": False,
    },
    "observability": {
        "prometheus_enabled": True,
        "health_check_interval": 30,
    },
}
