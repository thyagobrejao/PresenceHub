"""mDNS Presence Detector.

Detects devices using Multicast DNS (Bonjour/Avahi) service announcements.
Listens for mDNS responses on the local network to discover devices advertising
services like _http._tcp, _hap._tcp (HomeKit), _airplay._tcp, etc.

mDNS detection provides high confidence (+90) because it captures devices
actively announcing their presence with hostname and service metadata.
"""

from __future__ import annotations

import asyncio
import socket
from typing import Any

from config.loader import ConfigLoader
from core.bus import AsyncioEventBus
from core.types import normalize_mac
from detectors.base import BaseDetector
from models.enums import DetectionSource
from models.score import SOURCE_POINTS


class MdnsDetector(BaseDetector):
    """Detects devices via mDNS/DNS-SD service discovery.

    Uses zeroconf to listen for mDNS announcements on the local network.
    Devices are discovered when they respond to mDNS queries or announce
    their services.

    Confidence: +90 points (very high reliability, devices self-announce)
    """

    @property
    def name(self) -> str:
        return "mdns"

    def __init__(self, config: ConfigLoader, bus: AsyncioEventBus) -> None:
        super().__init__(config, bus)
        self._zeroconf = None
        self._browser = None
        self._discovered: set[str] = set()

    async def start(self) -> None:
        """Start the mDNS listener.

        Overrides BaseDetector.start() to also initialize the zeroconf
        service browser for continuous mDNS discovery.
        """
        await super().start()
        # Start zeroconf listener as a background task
        asyncio.create_task(self._listen_mdns(), name=f"mdns-listener-{self.name}")

    async def stop(self) -> None:
        """Stop the mDNS listener and clean up zeroconf resources."""
        if self._zeroconf:
            try:
                await asyncio.to_thread(self._zeroconf.close)
            except Exception:
                pass
            self._zeroconf = None
        await super().stop()

    async def _scan_impl(self) -> None:
        """Execute a single mDNS discovery scan.

        Queries for common service types and publishes discovered devices.
        This runs periodically while the continuous listener catches
        real-time announcements.
        """
        conf = SOURCE_POINTS[DetectionSource.MDNS]
        discovered: list[dict[str, Any]] = []

        try:
            discovered = await asyncio.to_thread(self._query_mdns_services)
        except Exception:
            self._log.exception("mdns_scan_error")
            return

        if discovered:
            await self._publish_detections(
                discovered,
                source=str(DetectionSource.MDNS),
                confidence=conf,
            )
            self._log.debug("mdns_scan_complete", device_count=len(discovered))

    async def _listen_mdns(self) -> None:
        """Continuously listen for mDNS announcements using zeroconf.

        Runs a ServiceBrowser that listens for common service types
        and publishes discovered devices in real-time.
        """
        try:
            from zeroconf import ServiceBrowser, Zeroconf
            from zeroconf.asyncio import AsyncServiceInfo, AsyncZeroconf
        except ImportError:
            self._log.warning("zeroconf_not_available")
            return

        try:
            aiozc = AsyncZeroconf()
            self._zeroconf = aiozc  # type: ignore[assignment]

            # Common mDNS service types to listen for
            service_types = [
                "_http._tcp.local.",
                "_https._tcp.local.",
                "_hap._tcp.local.",          # HomeKit
                "_airplay._tcp.local.",      # AirPlay
                "_raop._tcp.local.",         # AirPlay 2
                "_smb._tcp.local.",          # Samba/Windows
                "_ssh._tcp.local.",          # SSH
                "_printer._tcp.local.",      # Printers
                "_googlecast._tcp.local.",   # Chromecast
                "_spotify-connect._tcp.local.",  # Spotify Connect
                "_companion-link._tcp.local.",   # Home Assistant Companion
            ]

            conf = SOURCE_POINTS[DetectionSource.MDNS]

            while self._running:
                for svc_type in service_types:
                    if not self._running:
                        break
                    try:
                        services = await aiozc.async_get_service_info(svc_type, timeout=2000)  # type: ignore[arg-type]
                    except Exception:
                        continue

                # Use ServiceBrowser for continuous discovery
                class MdnsListener:
                    def __init__(self, detector: MdnsDetector) -> None:
                        self.detector = detector

                    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:  # type: ignore[override]  # noqa: A002
                        asyncio.ensure_future(self._resolve_service(zc, type_, name))

                    async def _resolve_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                        try:
                            from zeroconf.asyncio import AsyncServiceInfo

                            info = AsyncServiceInfo(type_, name)
                            await info.async_request(zc, timeout=2000)

                            if info.addresses:
                                ip = socket.inet_ntoa(info.addresses[0])
                                hostname = info.server.rstrip(".") if info.server else name.split(".")[0]

                                # mDNS doesn't give us MAC directly, so we use IP+hostname
                                # MAC will be enriched later by cross-referencing ARP table
                                det = {
                                    "mac": "",  # Will be enriched by cross-reference
                                    "ip": ip,
                                    "hostname": hostname,
                                    "vendor": "",
                                    "extra": {
                                        "service_type": type_,
                                        "service_name": name,
                                        "port": str(info.port) if info.port else "",
                                    },
                                }
                                await self.detector._publish_detections(
                                    [det],
                                    source=str(DetectionSource.MDNS),
                                    confidence=conf,
                                )
                        except Exception:
                            pass

                listener = MdnsListener(self)
                browser = ServiceBrowser(aiozc.zeroconf, service_types, listener)  # type: ignore[arg-type]
                self._browser = browser

                # Keep the listener alive
                while self._running:
                    await asyncio.sleep(5)

                break

        except Exception:
            self._log.exception("mdns_listener_error")
        finally:
            if self._zeroconf:
                try:
                    await aiozc.async_close()
                except Exception:
                    pass

    def _query_mdns_services(self) -> list[dict[str, Any]]:
        """Perform a one-shot mDNS query using system tools (dns-sd / avahi-browse).

        Falls back to system commands when zeroconf library is unavailable
        or as a complementary discovery method.

        Returns:
            List of detection dictionaries.
        """
        import platform
        import subprocess

        system = platform.system().lower()
        results: list[dict[str, Any]] = []

        try:
            if system == "darwin":
                # macOS: dns-sd
                output = subprocess.run(
                    ["dns-sd", "-B", "_http._tcp", "local"],
                    capture_output=True, text=True, timeout=8,
                )
                # Parse dns-sd output for hostnames
                for line in output.stdout.split("\n"):
                    if "Add" in line or "Rmv" in line:
                        parts = line.split()
                        if len(parts) >= 7:
                            hostname = parts[3]
                            results.append({
                                "mac": "",
                                "ip": "",
                                "hostname": hostname,
                                "vendor": "",
                            })

            elif system == "linux":
                # Linux: avahi-browse
                output = subprocess.run(
                    ["avahi-browse", "-atrp"],
                    capture_output=True, text=True, timeout=8,
                )
                for line in output.stdout.split("\n"):
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split(";")
                    if len(parts) >= 8:
                        hostname = parts[3]
                        ip = parts[7] if len(parts) > 7 else ""
                        results.append({
                            "mac": "",
                            "ip": ip,
                            "hostname": hostname,
                            "vendor": "",
                        })

        except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
            pass

        return results
