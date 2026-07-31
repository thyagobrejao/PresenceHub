"""DHCP Lease File Presence Detector.

Detects devices by parsing DHCP lease files from common DHCP servers.
Supported formats:
    - dnsmasq
    - ISC DHCPd
    - OpenWRT (udhcpd)
    - systemd-networkd

DHCP detection provides high confidence (+80) because DHCP leases represent
actual IP assignments with MAC addresses and often hostnames.
"""

from __future__ import annotations

import asyncio
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.loader import ConfigLoader
from core.bus import AsyncioEventBus
from core.types import normalize_mac
from detectors.base import BaseDetector
from models.enums import DetectionSource
from models.score import SOURCE_POINTS


class DhcpDetector(BaseDetector):
    """Detects devices by parsing DHCP lease files.

    Reads lease files from common DHCP servers (dnsmasq, dhcpd, etc.)
    and extracts MAC, IP, hostname, and lease timestamps.

    Confidence: +80 points (high — definitive IP-to-MAC mapping from DHCP server)
    """

    @property
    def name(self) -> str:
        return "dhcp"

    def __init__(self, config: ConfigLoader, bus: AsyncioEventBus) -> None:
        super().__init__(config, bus)
        self._lease_paths = config.get("network", "dhcp_lease_paths", default=[])

    async def _scan_impl(self) -> None:
        """Parse all configured DHCP lease files and publish discovered devices."""
        conf = SOURCE_POINTS[DetectionSource.DHCP]
        all_leases: list[dict[str, Any]] = []

        for path in self._lease_paths:
            if not os.path.isfile(path):
                self._log.debug("lease_file_not_found", path=path)
                continue

            try:
                leases = await asyncio.to_thread(self._parse_lease_file, path)
                all_leases.extend(leases)
                self._log.debug("leases_parsed", path=path, count=len(leases))
            except Exception:
                self._log.exception("lease_parse_error", path=path)

        if all_leases:
            await self._publish_detections(
                all_leases,
                source=str(DetectionSource.DHCP),
                confidence=conf,
            )
            self._log.debug("dhcp_scan_complete", total_leases=len(all_leases))

    def _parse_lease_file(self, path: str) -> list[dict[str, Any]]:
        """Parse a DHCP lease file and extract device entries.

        Auto-detects the lease file format based on content.

        Args:
            path: Path to the lease file.

        Returns:
            List of detection dictionaries.
        """
        try:
            with open(path) as f:
                content = f.read()
        except OSError:
            return []

        if not content.strip():
            return []

        # Auto-detect format
        if "dnsmasq" in content.lower() or re.search(r"^\d+\s+", content, re.MULTILINE):
            return self._parse_dnsmasq_leases(content)
        elif "lease " in content.lower() and "{" in content:
            return self._parse_dhcpd_leases(content)
        elif re.search(r"^\s*[0-9a-fA-F:]+\s+", content, re.MULTILINE):
            return self._parse_udhcpd_leases(content)
        else:
            # Try dnsmasq as fallback (most common)
            return self._parse_dnsmasq_leases(content)

    def _parse_dnsmasq_leases(self, content: str) -> list[dict[str, Any]]:
        """Parse dnsmasq lease file format.

        Format:
            <lease_expiry> <mac> <ip> <hostname> <client_id>

        Example:
            1234567890 aa:bb:cc:dd:ee:ff 192.168.1.100 myphone 01:aa:bb:cc:dd:ee:ff

        Returns:
            List of detection dictionaries.
        """
        leases: list[dict[str, Any]] = []

        for line in content.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if len(parts) < 3:
                continue

            # dnsmasq: timestamp mac ip [hostname] [client_id]
            try:
                timestamp = int(parts[0])
            except ValueError:
                continue

            mac_raw = parts[1]
            ip = parts[2]
            hostname = parts[3] if len(parts) > 3 else ""
            # Skip client_id (parts[4]) if present — it's often the MAC again

            # Filter invalid MACs
            if mac_raw.lower() in ("00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff"):
                continue

            try:
                mac = normalize_mac(mac_raw)
            except ValueError:
                continue

            # Check if lease is active (not expired)
            now_ts = datetime.now(timezone.utc).timestamp()
            is_active = timestamp == 0 or timestamp > now_ts

            # Always include the lease, even if expired (it's still recent evidence)
            lease_entry: dict[str, Any] = {
                "mac": mac,
                "ip": ip,
                "hostname": hostname,
                "vendor": "",
                "extra": {
                    "lease_expiry": str(timestamp),
                    "is_active": str(is_active),
                    "lease_file": "dnsmasq",
                },
            }
            leases.append(lease_entry)

        return leases

    def _parse_dhcpd_leases(self, content: str) -> list[dict[str, Any]]:
        """Parse ISC DHCPd lease file format.

        Format:
            lease 192.168.1.100 {
              starts 4 2024/01/15 10:00:00;
              ends 5 2024/01/16 10:00:00;
              hardware ethernet aa:bb:cc:dd:ee:ff;
              client-hostname "myphone";
            }

        Returns:
            List of detection dictionaries.
        """
        leases: list[dict[str, Any]] = []

        # Split into lease blocks
        blocks = re.split(r"(?=lease\s+)", content)

        for block in blocks:
            if not block.strip():
                continue

            # Extract IP
            ip_match = re.search(r"lease\s+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", block)
            if not ip_match:
                continue
            ip = ip_match.group(1)

            # Extract MAC
            mac_match = re.search(r"hardware\s+ethernet\s+([0-9a-fA-F:]+)", block)
            if not mac_match:
                continue
            mac_raw = mac_match.group(1)

            if mac_raw.lower() in ("00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff"):
                continue

            try:
                mac = normalize_mac(mac_raw)
            except ValueError:
                continue

            # Extract hostname
            hostname = ""
            host_match = re.search(r'client-hostname\s+"([^"]+)"', block)
            if host_match:
                hostname = host_match.group(1)

            # Extract end time
            ends_match = re.search(r"ends\s+\d+\s+([^;]+)", block)
            is_active = True
            if ends_match:
                try:
                    from datetime import datetime as dt

                    ends_str = ends_match.group(1).strip()
                    ends_dt = dt.strptime(ends_str, "%Y/%m/%d %H:%M:%S")
                    ends_dt = ends_dt.replace(tzinfo=timezone.utc)
                    is_active = ends_dt > datetime.now(timezone.utc)
                except ValueError:
                    pass

            lease_entry: dict[str, Any] = {
                "mac": mac,
                "ip": ip,
                "hostname": hostname,
                "vendor": "",
                "extra": {
                    "is_active": str(is_active),
                    "lease_file": "dhcpd",
                },
            }
            leases.append(lease_entry)

        return leases

    def _parse_udhcpd_leases(self, content: str) -> list[dict[str, Any]]:
        """Parse udhcpd (OpenWRT) lease file format.

        Format:
            <mac> <ip> <hostname> <client_id>

        Example:
            AA:BB:CC:DD:EE:FF 192.168.1.100 myphone *

        Returns:
            List of detection dictionaries.
        """
        leases: list[dict[str, Any]] = []

        for line in content.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            mac_raw = parts[0]
            ip = parts[1]
            hostname = parts[2] if len(parts) > 2 and parts[2] != "*" else ""

            if mac_raw.lower() in ("00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff"):
                continue

            try:
                mac = normalize_mac(mac_raw)
            except ValueError:
                continue

            lease_entry: dict[str, Any] = {
                "mac": mac,
                "ip": ip,
                "hostname": hostname,
                "vendor": "",
                "extra": {
                    "is_active": "True",
                    "lease_file": "udhcpd",
                },
            }
            leases.append(lease_entry)

        return leases
