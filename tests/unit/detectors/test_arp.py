"""Unit tests for the ArpDetector."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from core.bus import AsyncioEventBus
from core.events import EventType
from detectors.arp.detector import ArpDetector


class TestArpDetector:
    """Tests for ArpDetector lifecycle and scanning."""

    @pytest.fixture
    def detector(self, config, event_bus: AsyncioEventBus) -> ArpDetector:
        return ArpDetector(config, event_bus)

    @pytest.mark.unit
    async def test_name(self, detector: ArpDetector) -> None:
        """Verify the detector name is 'arp'."""
        assert detector.name == "arp"

    @pytest.mark.unit
    async def test_start_stop_lifecycle(self, detector: ArpDetector) -> None:
        """Verify detector starts and stops cleanly."""
        # Mock _scan_impl to prevent actual scanning
        with patch.object(detector, "_scan_impl", new_callable=AsyncMock):
            await detector.start()
            assert detector.is_running is True

            await asyncio.sleep(0.1)  # Let the loop start

            await detector.stop()
            assert detector.is_running is False

    @pytest.mark.unit
    async def test_start_publishes_event(self, detector: ArpDetector, event_bus: AsyncioEventBus) -> None:
        """Verify starting publishes DETECTOR_STARTED event."""
        received: list[dict] = []

        async def handler(payload: dict) -> None:
            received.append(payload)

        event_bus.subscribe(EventType.DETECTOR_STARTED, handler)

        with patch.object(detector, "_scan_impl", new_callable=AsyncMock):
            await detector.start()
            await asyncio.sleep(0.1)
            await detector.stop()

        assert len(received) >= 1
        assert received[0]["detector"] == "arp"

    @pytest.mark.unit
    async def test_stop_publishes_event(self, detector: ArpDetector, event_bus: AsyncioEventBus) -> None:
        """Verify stopping publishes DETECTOR_STOPPED event."""
        received: list[dict] = []

        async def handler(payload: dict) -> None:
            received.append(payload)

        event_bus.subscribe(EventType.DETECTOR_STOPPED, handler)

        with patch.object(detector, "_scan_impl", new_callable=AsyncMock):
            await detector.start()
            await asyncio.sleep(0.1)
            await detector.stop()

            # Wait for events to be processed
            await asyncio.sleep(0.1)

        assert len(received) >= 1
        assert received[0]["detector"] == "arp"

    @pytest.mark.unit
    async def test_double_start_safe(self, detector: ArpDetector) -> None:
        """Verify calling start twice is safe (idempotent)."""
        with patch.object(detector, "_scan_impl", new_callable=AsyncMock):
            await detector.start()
            await detector.start()  # Second start should be safe
            await asyncio.sleep(0.1)
            await detector.stop()

    @pytest.mark.unit
    async def test_health_check_running(self, detector: ArpDetector) -> None:
        """Verify health check returns True when running."""
        with patch.object(detector, "_scan_impl", new_callable=AsyncMock):
            await detector.start()
            await asyncio.sleep(0.1)
            assert await detector.health_check() is True
            await detector.stop()

    @pytest.mark.unit
    async def test_health_check_stopped(self, detector: ArpDetector) -> None:
        """Verify health check returns False when stopped."""
        assert await detector.health_check() is False

    @pytest.mark.unit
    async def test_read_linux_arp_parsing(self, detector: ArpDetector) -> None:
        """Verify Linux /proc/net/arp parsing."""
        sample = (
            "IP address       HW type     Flags       HW address            Mask     Device\n"
            "192.168.1.1      0x1         0x2         aa:bb:cc:dd:ee:ff     *        eth0\n"
            "192.168.1.100    0x1         0x2         11:22:33:44:55:66     *        eth0\n"
            "192.168.1.200    0x1         0x0         00:00:00:00:00:00     *        eth0\n"
        )

        with patch("builtins.open", side_effect=Exception("not used")):
            pass

        # Test the parsing logic by mocking open
        import io

        mock_file = io.StringIO(sample)
        with patch("builtins.open", return_value=mock_file):
            results = detector._read_linux_arp()
            assert len(results) == 2  # Incomplete entry should be filtered
            assert results[0]["mac"] == "AA:BB:CC:DD:EE:FF"
            assert results[0]["ip"] == "192.168.1.1"
            assert results[1]["mac"] == "11:22:33:44:55:66"
            assert results[1]["ip"] == "192.168.1.100"

    @pytest.mark.unit
    async def test_read_bsd_arp_parsing(self, detector: ArpDetector) -> None:
        """Verify BSD/macOS 'arp -a' parsing."""
        sample = (
            "? (192.168.1.1) at aa:bb:cc:dd:ee:ff on en0 ifscope [ethernet]\n"
            "myhost.local (192.168.1.100) at 11:22:33:44:55:66 on en0 [ethernet]\n"
            "? (192.168.1.254) at ff:ff:ff:ff:ff:ff on en0 ifscope [ethernet]\n"
        )

        with patch.object(detector, "_run_arp_command", return_value=sample):
            results = detector._read_bsd_arp()
            assert len(results) == 2  # Broadcast MAC filtered
            assert results[0]["mac"] == "AA:BB:CC:DD:EE:FF"
            assert results[0]["ip"] == "192.168.1.1"
            assert results[1]["mac"] == "11:22:33:44:55:66"
            assert results[1]["ip"] == "192.168.1.100"
            assert results[1]["hostname"] == "myhost.local"

    @pytest.mark.unit
    async def test_scan_publishes_detections(self, detector: ArpDetector, event_bus: AsyncioEventBus) -> None:
        """Verify that scan results are published as DEVICE_DETECTED events."""
        received: list[dict] = []

        async def handler(payload: dict) -> None:
            received.append(payload)

        event_bus.subscribe(EventType.DEVICE_DETECTED, handler)

        sample_entries = [
            {"mac": "AA:BB:CC:DD:EE:FF", "ip": "192.168.1.1", "hostname": "", "vendor": ""},
            {"mac": "11:22:33:44:55:66", "ip": "192.168.1.100", "hostname": "laptop", "vendor": "Apple"},
        ]

        with patch.object(detector, "_read_arp_table", return_value=sample_entries):
            await detector._scan_impl()

        # Wait for async event handlers
        await asyncio.sleep(0.1)

        assert len(received) == 2
        assert received[0]["mac"] == "AA:BB:CC:DD:EE:FF"
        assert received[0]["source"] == "arp"
        assert received[1]["mac"] == "11:22:33:44:55:66"
        assert received[1]["hostname"] == "laptop"
