"""Core types and type aliases for the PresenceHub system.

All shared types are defined here to ensure consistency across the entire codebase.
"""

from typing import NewType, TypeAlias

# Strongly-typed identifiers
MacAddress = NewType("MacAddress", str)
"""A MAC address in the format AA:BB:CC:DD:EE:FF (uppercase, colon-separated)."""

DeviceId = NewType("DeviceId", str)
"""A unique device identifier (typically the MAC address)."""

Hostname = NewType("Hostname", str)
"""A device hostname."""

IPv4Address = NewType("IPv4Address", str)
"""An IPv4 address string."""

# Type aliases for readability
ConfidenceValue: TypeAlias = int
"""Confidence score value, typically in range 0-100."""

JsonDict: TypeAlias = dict[str, object]
"""Generic JSON-compatible dictionary."""

EventPayload: TypeAlias = dict[str, object]
"""Payload carried by domain events."""


def normalize_mac(mac: str) -> MacAddress:
    """Normalize a MAC address to uppercase colon-separated format.

    Args:
        mac: Raw MAC address string (supports :, -, . separators, or no separator).

    Returns:
        Normalized MAC address.

    Raises:
        ValueError: If the MAC address format is invalid.
    """
    mac = mac.strip().upper()
    # Remove common separators
    for sep in (":", "-", "."):
        mac = mac.replace(sep, "")
    if len(mac) != 12:
        raise ValueError(f"Invalid MAC address length: {mac!r} (expected 12 hex chars)")
    try:
        int(mac, 16)
    except ValueError as exc:
        raise ValueError(f"Invalid MAC address hex chars: {mac!r}") from exc
    return MacAddress(":".join(mac[i : i + 2] for i in range(0, 12, 2)))
