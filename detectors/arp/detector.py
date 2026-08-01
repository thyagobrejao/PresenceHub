"""ARP Presence Detector.

Scans the local network using ARP (Address Resolution Protocol) to discover
active devices. Uses the system ARP table and optional Scapy-based active scanning.

ARP is the most reliable detection source (+100 confidence) because it directly
reflects the kernel's knowledge of which devices are communicating on the network.
"""

from __future__ import annotations

import asyncio
import re
import subprocess
from typing import Any

from config.loader import ConfigLoader
from core.bus import AsyncioEventBus
from core.types import Hostname, IPv4Address, MacAddress, normalize_mac
from detectors.base import BaseDetector
from models.enums import DetectionSource
from models.score import SOURCE_POINTS


class ArpDetector(BaseDetector):
    """Detects devices by reading the system ARP table.

    The ARP table contains MAC-to-IP mappings for all devices that have
    recently communicated on the local network segment.

    Scanning modes:
        1. System ARP table (arp -a / /proc/net/arp) — fast, no privileges needed
        2. Scapy ARP scan — active scan of the subnet (requires root/cap_net_raw)

    Confidence: +100 points (highest reliability)
    """

    @property
    def name(self) -> str:
        return "arp"

    def __init__(self, config: ConfigLoader, bus: AsyncioEventBus) -> None:
        super().__init__(config, bus)

    async def _scan_impl(self) -> None:
        """Execute a single ARP scan.

        Reads the system ARP table, parses entries, and publishes
        each detected device to the EventBus.
        """
        try:
            entries = await asyncio.to_thread(self._read_arp_table)
        except Exception:
            self._log.exception("arp_table_read_failed")
            return

        if not entries:
            self._log.debug("arp_table_empty")
            return

        confidence = SOURCE_POINTS[DetectionSource.ARP]
        await self._publish_detections(
            entries,
            source=str(DetectionSource.ARP),
            confidence=confidence,
        )
        self._log.debug("arp_scan_complete", device_count=len(entries))

    def _read_arp_table(self) -> list[dict[str, Any]]:
        """Read the system ARP table and parse entries.

        Tries platform-specific methods in order:
            1. Linux: /proc/net/arp
            2. macOS/BSD: arp -a
            3. Windows: arp -a

        Returns:
            List of detection dictionaries with mac, ip, hostname, vendor fields.
        """
        import platform

        system = platform.system().lower()

        if system == "linux":
            return self._read_linux_arp()
        elif system in ("darwin", "freebsd", "openbsd"):
            return self._read_bsd_arp()
        elif system == "windows":
            return self._read_windows_arp()
        else:
            self._log.warning("unsupported_platform", platform=system)
            return []

    def _read_linux_arp(self) -> list[dict[str, Any]]:
        """Read ARP neighbor table using 'ip neigh' (Linux).

        Uses 'ip neigh' instead of /proc/net/arp because it exposes
        the NUD (Neighbour Unreachability Detection) state:
            REACHABLE — confirmed alive recently
            STALE     — was alive but unconfirmed (device may be gone)
            DELAY     — kernel is about to probe
            PROBE     — actively probing
            FAILED    — not reachable
            INCOMPLETE — resolution in progress

        Only REACHABLE and DELAY entries are treated as valid detections.
        STALE entries are ignored to allow fast offline detection.

        Returns:
            List of parsed ARP entries for devices confirmed alive.
        """
        entries: list[dict[str, Any]] = []
        try:
            result = subprocess.run(
                ["ip", "neigh"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = result.stdout
        except (subprocess.TimeoutExpired, OSError) as exc:
            self._log.warning("ip_neigh_failed", error=str(exc))
            # Fallback to /proc/net/arp
            return self._read_proc_net_arp()

        if not output:
            return entries

        # Format: 192.168.1.1 dev eth0 lladdr aa:bb:cc:dd:ee:ff REACHABLE
        for line in output.strip().split("\n"):
            parts = line.strip().split()
            if len(parts) < 4:
                continue

            ip = parts[0]

            # Find MAC address (lladdr field)
            try:
                lladdr_idx = parts.index("lladdr")
                mac = parts[lladdr_idx + 1]
            except (ValueError, IndexError):
                continue

            # Get NUD state (last field)
            state = parts[-1].upper()

            # Ignore entries in FAILED or INCOMPLETE states
            if state in ("FAILED", "INCOMPLETE"):
                continue

            if mac.lower() in ("00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff"):
                continue

            try:
                normalized_mac = normalize_mac(mac)
            except ValueError:
                continue

            entries.append({
                "mac": normalized_mac,
                "ip": ip,
                "hostname": "",
                "vendor": "",
            })

        return entries

    def _read_proc_net_arp(self) -> list[dict[str, Any]]:
        """Fallback: Read ARP table from /proc/net/arp (Linux).

        Used only when 'ip neigh' is unavailable.

        Returns:
            List of parsed ARP entries.
        """
        entries: list[dict[str, Any]] = []
        try:
            with open("/proc/net/arp") as f:
                lines = f.readlines()
        except OSError as exc:
            self._log.warning("proc_net_arp_read_failed", error=str(exc))
            return entries

        for line in lines[1:]:
            parts = line.strip().split()
            if len(parts) < 4:
                continue

            ip = parts[0]
            flags = parts[2]
            mac = parts[3]

            if flags == "0x0" or mac == "00:00:00:00:00:00":
                continue

            try:
                normalized_mac = normalize_mac(mac)
            except ValueError:
                continue

            entries.append({
                "mac": normalized_mac,
                "ip": ip,
                "hostname": "",
                "vendor": "",
            })

        return entries

    def _read_bsd_arp(self) -> list[dict[str, Any]]:
        """Read ARP table using 'arp -a' (macOS/BSD).

        Format examples:
            ? (192.168.1.1) at aa:bb:cc:dd:ee:ff on en0 ifscope [ethernet]
            myhost.local (192.168.1.100) at aa:bb:cc:dd:ee:ff on en0 [ethernet]

        Returns:
            List of parsed ARP entries.
        """
        entries: list[dict[str, Any]] = []
        output = self._run_arp_command()

        if not output:
            return entries

        # Regex to match arp -a output on BSD/macOS
        pattern = re.compile(
            r"\??\s*\(?([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\)?\s+at\s+"
            r"([0-9a-fA-F]{1,2}:[0-9a-fA-F]{1,2}:[0-9a-fA-F]{1,2}:[0-9a-fA-F]{1,2}:[0-9a-fA-F]{1,2}:[0-9a-fA-F]{1,2})"
        )

        for line in output.split("\n"):
            match = pattern.search(line)
            if not match:
                continue

            ip = match.group(1)
            mac = match.group(2)

            if mac.lower() in ("ff:ff:ff:ff:ff:ff", "00:00:00:00:00:00"):
                continue

            try:
                normalized_mac = normalize_mac(mac)
            except ValueError:
                continue

            # Try to extract hostname from parentheses before IP
            hostname_match = re.match(r"(\S+)\s+\([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+\)", line)
            hostname = hostname_match.group(1) if hostname_match else ""

            entries.append({
                "mac": normalized_mac,
                "ip": ip,
                "hostname": hostname if hostname != "?" else "",
                "vendor": "",
            })

        return entries

    def _read_windows_arp(self) -> list[dict[str, Any]]:
        """Read ARP table using 'arp -a' (Windows).

        Returns:
            List of parsed ARP entries.
        """
        entries: list[dict[str, Any]] = []
        output = self._run_arp_command()

        if not output:
            return entries

        # Windows format: 192.168.1.1          aa-bb-cc-dd-ee-ff     dynamic
        pattern = re.compile(
            r"([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\s+"
            r"([0-9a-fA-F]{1,2}-[0-9a-fA-F]{1,2}-[0-9a-fA-F]{1,2}-[0-9a-fA-F]{1,2}-[0-9a-fA-F]{1,2}-[0-9a-fA-F]{1,2})"
        )

        for line in output.split("\n"):
            match = pattern.search(line)
            if not match:
                continue

            ip = match.group(1)
            mac = match.group(2)

            if mac.lower() in ("ff-ff-ff-ff-ff-ff", "00-00-00-00-00-00"):
                continue

            try:
                normalized_mac = normalize_mac(mac)
            except ValueError:
                continue

            entries.append({
                "mac": normalized_mac,
                "ip": ip,
                "hostname": "",
                "vendor": "",
            })

        return entries

    def _run_arp_command(self) -> str:
        """Run the system 'arp -a' command.

        Returns:
            Command output as string, or empty string on failure.
        """
        try:
            result = subprocess.run(
                ["arp", "-a"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout
        except (subprocess.TimeoutExpired, OSError) as exc:
            self._log.warning("arp_command_failed", error=str(exc))
            return ""
