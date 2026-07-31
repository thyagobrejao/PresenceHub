"""Unit tests for the PingDetector."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from core.events import EventType
from detectors.ping.detector import PingDetector


class TestPingDetector:
    """Tests for PingDetector lifecycle and ping operations."""

    @pytest.fixture
    def detector(self, config, event_bus) -> PingDetector:
        return PingDetector(config, event_bus)

    @pytest.mark.unit
    async def test_name(self, detector: PingDetector) -> None:
        """Verify the detector name is 'ping'."""
        assert detector.name == "ping"

    @pytest.mark.unit
    async def test_start_stop_lifecycle(self, detector: PingDetector) -> None:
        """Verify detector starts and stops cleanly."""
        with patch.object(detector, "_scan_impl", new_callable=AsyncMock):
            await detector.start()
            assert detector.is_running is True
            await asyncio.sleep(0.1)
            await detector.stop()
            assert detector.is_running is False

    @pytest.mark.unit
    async def test_get_ping_targets(self, detector: PingDetector) -> None:
        """Verify target IP generation from subnet."""
        targets = detector._get_ping_targets()
        assert len(targets) > 0
        assert "192.168.1.1" in targets  # Gateway
        # Should have gateway + some host IPs
        assert len(targets) >= 10

    @pytest.mark.unit
    async def test_ping_host_success(self, detector: PingDetector) -> None:
        """Verify _ping_host returns data on successful ping."""
        mock_output = "PING myhost.local (192.168.1.100): 56 data bytes\n64 bytes from 192.168.1.100: icmp_seq=0 ttl=64 time=1.2 ms\n"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = mock_output

            result = detector._ping_host("192.168.1.100")
            assert result is not None
            assert result["ip"] == "192.168.1.100"
            assert result["hostname"] == "myhost.local"

    @pytest.mark.unit
    async def test_ping_host_failure(self, detector: PingDetector) -> None:
        """Verify _ping_host returns None on failed ping."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ""

            result = detector._ping_host("192.168.1.254")
            assert result is None

    @pytest.mark.unit
    async def test_extract_hostname(self, detector: PingDetector) -> None:
        """Verify hostname extraction from ping output."""
        output = "PING my-device.local (192.168.1.100): 56 data bytes\n"
        hostname = detector._extract_hostname(output, "192.168.1.100")
        assert hostname == "my-device.local"

    @pytest.mark.unit
    async def test_extract_hostname_no_hostname(self, detector: PingDetector) -> None:
        """Verify empty hostname when ping output has no hostname."""
        output = "PING 192.168.1.1 (192.168.1.1): 56 data bytes\n"
        hostname = detector._extract_hostname(output, "192.168.1.1")
        assert hostname == ""

    @pytest.mark.unit
    async def test_scan_publishes_detections(self, detector: PingDetector, event_bus) -> None:
        """Verify scan publishes DEVICE_DETECTED events."""
        received: list[dict] = []

        async def handler(payload: dict) -> None:
            received.append(payload)

        event_bus.subscribe(EventType.DEVICE_DETECTED, handler)

        # Mock ping responses: some hosts alive, some not
        alive = {"ip": "192.168.1.1", "hostname": "gateway", "vendor": ""}

        with patch.object(detector, "_ping_host", return_value=alive):
            with patch.object(detector, "_get_ping_targets", return_value=["192.168.1.1"]):
                await detector._scan_impl()

        # Wait for async event handlers to process
        await asyncio.sleep(0.3)
        assert len(received) >= 1
        assert received[0]["source"] == "ping"

    @pytest.mark.unit
    async def test_ping_single(self, detector: PingDetector) -> None:
        """Verify convenience method ping_single."""
        with patch.object(detector, "_ping_host", return_value={"ip": "192.168.1.1"}):
            result = await detector.ping_single("192.168.1.1")
            assert result is True

        with patch.object(detector, "_ping_host", return_value=None):
            result = await detector.ping_single("192.168.1.254")
            assert result is False
