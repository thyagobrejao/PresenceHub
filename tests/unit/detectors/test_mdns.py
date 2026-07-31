"""Unit tests for the MdnsDetector."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from core.events import EventType
from detectors.mdns.detector import MdnsDetector


class TestMdnsDetector:
    """Tests for MdnsDetector lifecycle and discovery."""

    @pytest.fixture
    def detector(self, config, event_bus) -> MdnsDetector:
        return MdnsDetector(config, event_bus)

    @pytest.mark.unit
    async def test_name(self, detector: MdnsDetector) -> None:
        """Verify the detector name is 'mdns'."""
        assert detector.name == "mdns"

    @pytest.mark.unit
    async def test_start_stop_lifecycle(self, detector: MdnsDetector) -> None:
        """Verify detector starts and stops cleanly."""
        with patch.object(detector, "_scan_impl", new_callable=AsyncMock):
            await detector.start()
            assert detector.is_running is True
            await asyncio.sleep(0.1)
            await detector.stop()
            assert detector.is_running is False

    @pytest.mark.unit
    async def test_health_check(self, detector: MdnsDetector) -> None:
        """Verify health check reflects running state."""
        with patch.object(detector, "_scan_impl", new_callable=AsyncMock):
            await detector.start()
            await asyncio.sleep(0.1)
            assert await detector.health_check() is True
            await detector.stop()
            assert await detector.health_check() is False

    @pytest.mark.unit
    async def test_scan_publishes_discoveries(self, detector: MdnsDetector, event_bus) -> None:
        """Verify scan publishes DEVICE_DETECTED events."""
        received: list[dict] = []

        async def handler(payload: dict) -> None:
            received.append(payload)

        event_bus.subscribe(EventType.DEVICE_DETECTED, handler)

        mock_discoveries = [
            {"mac": "", "ip": "192.168.1.100", "hostname": "myphone.local", "vendor": ""},
            {"mac": "", "ip": "192.168.1.101", "hostname": "tv.local", "vendor": ""},
        ]

        with patch.object(detector, "_query_mdns_services", return_value=mock_discoveries):
            await detector._scan_impl()

        # Wait for async event handlers to process
        await asyncio.sleep(0.3)
        assert len(received) == 2
        assert received[0]["hostname"] == "myphone.local"
        assert received[0]["source"] == "mdns"
        assert received[1]["hostname"] == "tv.local"
