"""ICMP Ping Presence Detector.

Detects device presence by sending ICMP Echo Request packets (ping) to known
IP addresses. Uses the system ping command for reliability and asyncio.to_thread
for non-blocking operation.

Ping provides moderate confidence (+40) because it's a direct reachability test,
but some devices block ICMP or have power-saving modes that delay responses.
"""

from __future__ import annotations

import asyncio
import ipaddress
import platform
import re
import subprocess
from typing import Any

from config.loader import ConfigLoader
from core.bus import AsyncioEventBus
from detectors.base import BaseDetector
from models.enums import DetectionSource
from models.score import SOURCE_POINTS


class PingDetector(BaseDetector):
    """Detects devices by sending ICMP ping requests.

    Pings known IPs from the device cache or scans the configured subnet.
    Devices that respond to ping are marked as online.

    Confidence: +40 points (moderate — some devices block/ignore ICMP)
    """

    @property
    def name(self) -> str:
        return "ping"

    def __init__(self, config: ConfigLoader, bus: AsyncioEventBus) -> None:
        super().__init__(config, bus)
        self._timeout = config.get("network", "ping_timeout", default=2)
        self._count = config.get("network", "ping_count", default=1)
        self._subnet = config.get("network", "subnet", default="192.168.1.0/24")

    async def _scan_impl(self) -> None:
        """Execute a ping sweep of known IPs or subnet.

        Strategy:
            1. Ping the gateway and known devices
            2. Optionally sweep the entire subnet (configurable)
        """
        conf = SOURCE_POINTS[DetectionSource.PING]
        targets = self._get_ping_targets()

        if not targets:
            self._log.debug("no_ping_targets")
            return

        # Ping targets concurrently in batches
        results = await self._ping_batch(targets)

        if results:
            await self._publish_detections(
                results,
                source=str(DetectionSource.PING),
                confidence=conf,
            )
            self._log.debug("ping_scan_complete", total=len(targets), alive=len(results))

    def _get_ping_targets(self) -> list[str]:
        """Get the list of IPs to ping.

        Scans all usable hosts in the configured subnet.

        Returns:
            List of IP addresses to ping.
        """
        targets: list[str] = []

        try:
            network = ipaddress.IPv4Network(self._subnet, strict=False)
            # Iterate all usable hosts in the subnet (excludes network and broadcast)
            for host in network.hosts():
                targets.append(str(host))
        except ValueError:
            self._log.warning("invalid_subnet", subnet=self._subnet)

        self._log.debug("ping_targets_resolved", count=len(targets), subnet=self._subnet)
        return targets

    async def _ping_batch(self, ips: list[str]) -> list[dict[str, Any]]:
        """Ping a batch of IPs concurrently using the system ping command.

        Args:
            ips: List of IP addresses to ping.

        Returns:
            List of detection dicts for responsive IPs.
        """
        # Process in chunks to avoid overwhelming the system
        chunk_size = 20
        results: list[dict[str, Any]] = []

        for i in range(0, len(ips), chunk_size):
            chunk = ips[i : i + chunk_size]
            tasks = [asyncio.to_thread(self._ping_host, ip) for ip in chunk]
            chunk_results = await asyncio.gather(*tasks, return_exceptions=True)

            for j, result in enumerate(chunk_results):
                if isinstance(result, Exception):
                    continue
                if result:
                    results.append(result)

        return results

    def _ping_host(self, ip: str) -> dict[str, Any] | None:
        """Ping a single host using the system ping command.

        Args:
            ip: IP address to ping.

        Returns:
            Detection dict if the host responds, None otherwise.
        """
        system = platform.system().lower()

        try:
            if system == "windows":
                cmd = ["ping", "-n", str(self._count), "-w", str(self._timeout * 1000), ip]
            else:
                cmd = ["ping", "-c", str(self._count), "-W", str(self._timeout), ip]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout + 2,
            )

            if result.returncode == 0:
                # Try to extract hostname from ping output
                hostname = self._extract_hostname(result.stdout, ip)
                return {
                    "mac": "",  # Ping doesn't give us MAC
                    "ip": ip,
                    "hostname": hostname,
                    "vendor": "",
                }

        except (subprocess.TimeoutExpired, OSError):
            pass

        return None

    def _extract_hostname(self, output: str, ip: str) -> str:
        """Extract hostname from ping output if available.

        Args:
            output: Ping command stdout.
            ip: The IP being pinged.

        Returns:
            Hostname string or empty string.
        """
        # macOS/Linux: PING hostname.local (192.168.1.x)
        match = re.match(r"PING\s+(\S+)\s+\(", output)
        if match:
            name = match.group(1)
            if name != ip:
                return name
        return ""

    async def ping_single(self, ip: str) -> bool:
        """Check if a single IP is reachable.

        Convenience method for other components to check reachability.

        Args:
            ip: IP address to ping.

        Returns:
            True if the host responds to ping.
        """
        result = await asyncio.to_thread(self._ping_host, ip)
        return result is not None
