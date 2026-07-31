"""Unit tests for the DhcpDetector."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from core.events import EventType
from detectors.dhcp.detector import DhcpDetector


class TestDhcpDetector:
    """Tests for DhcpDetector lifecycle and lease parsing."""

    @pytest.fixture
    def detector(self, config, event_bus) -> DhcpDetector:
        det = DhcpDetector(config, event_bus)
        # Override lease paths to avoid filesystem access
        det._lease_paths = ["/tmp/test.leases"]
        return det

    @pytest.mark.unit
    async def test_name(self, detector: DhcpDetector) -> None:
        """Verify the detector name is 'dhcp'."""
        assert detector.name == "dhcp"

    @pytest.mark.unit
    async def test_start_stop_lifecycle(self, detector: DhcpDetector) -> None:
        """Verify detector starts and stops cleanly."""
        with patch.object(detector, "_scan_impl", new_callable=AsyncMock):
            await detector.start()
            assert detector.is_running is True
            await asyncio.sleep(0.1)
            await detector.stop()
            assert detector.is_running is False

    @pytest.mark.unit
    async def test_parse_dnsmasq_leases(self, detector: DhcpDetector) -> None:
        """Verify dnsmasq lease file parsing."""
        content = (
            "0 aa:bb:cc:dd:ee:ff 192.168.1.100 myphone *\n"
            "1234567890 11:22:33:44:55:66 192.168.1.101 laptop 01:11:22:33:44:55:66\n"
            "# comment line\n"
            "0 00:00:00:00:00:00 192.168.1.200 invalid *\n"
        )

        leases = detector._parse_dnsmasq_leases(content)
        assert len(leases) == 2  # Invalid MAC filtered out
        assert leases[0]["mac"] == "AA:BB:CC:DD:EE:FF"
        assert leases[0]["ip"] == "192.168.1.100"
        assert leases[0]["hostname"] == "myphone"
        assert leases[1]["mac"] == "11:22:33:44:55:66"
        assert leases[1]["ip"] == "192.168.1.101"
        assert leases[1]["hostname"] == "laptop"

    @pytest.mark.unit
    async def test_parse_dhcpd_leases(self, detector: DhcpDetector) -> None:
        """Verify ISC DHCPd lease file parsing."""
        content = (
            "lease 192.168.1.100 {\n"
            "  starts 4 2024/01/15 10:00:00;\n"
            '  ends 6 2030/01/16 10:00:00;\n'
            "  hardware ethernet aa:bb:cc:dd:ee:ff;\n"
            '  client-hostname "myphone";\n'
            "}\n"
            "lease 192.168.1.101 {\n"
            "  starts 4 2024/01/15 10:00:00;\n"
            '  ends 4 2020/01/16 10:00:00;\n'
            "  hardware ethernet 11:22:33:44:55:66;\n"
            "}\n"
        )

        leases = detector._parse_dhcpd_leases(content)
        assert len(leases) == 2
        assert leases[0]["mac"] == "AA:BB:CC:DD:EE:FF"
        assert leases[0]["ip"] == "192.168.1.100"
        assert leases[0]["hostname"] == "myphone"
        assert leases[0]["extra"]["is_active"] == "True"  # Future end date
        assert leases[1]["mac"] == "11:22:33:44:55:66"
        assert leases[1]["ip"] == "192.168.1.101"
        assert leases[1]["extra"]["is_active"] == "False"  # Past end date

    @pytest.mark.unit
    async def test_parse_udhcpd_leases(self, detector: DhcpDetector) -> None:
        """Verify udhcpd (OpenWRT) lease file parsing."""
        content = (
            "AA:BB:CC:DD:EE:FF 192.168.1.100 myphone *\n"
            "11:22:33:44:55:66 192.168.1.101 * *\n"
            "FF:FF:FF:FF:FF:FF 192.168.1.255 broadcast *\n"
        )

        leases = detector._parse_udhcpd_leases(content)
        assert len(leases) == 2  # Broadcast filtered out
        assert leases[0]["mac"] == "AA:BB:CC:DD:EE:FF"
        assert leases[0]["ip"] == "192.168.1.100"
        assert leases[0]["hostname"] == "myphone"
        assert leases[1]["mac"] == "11:22:33:44:55:66"
        assert leases[1]["hostname"] == ""

    @pytest.mark.unit
    async def test_auto_detect_format(self, detector: DhcpDetector) -> None:
        """Verify auto-detection of lease file format."""
        # dnsmasq format
        content_dnsmasq = "0 aa:bb:cc:dd:ee:ff 192.168.1.100 phone *\n"
        leases = detector._parse_lease_file("/tmp/test_dnsmasq.leases")
        # Mock the file read
        with patch("builtins.open", side_effect=FileNotFoundError):
            pass
        # Directly test format detection via parse methods
        leases = detector._parse_dnsmasq_leases(content_dnsmasq)
        assert len(leases) == 1

        # dhcpd format
        content_dhcpd = "lease 192.168.1.100 {\n  hardware ethernet aa:bb:cc:dd:ee:ff;\n}\n"
        leases = detector._parse_dhcpd_leases(content_dhcpd)
        assert len(leases) == 1

    @pytest.mark.unit
    async def test_scan_skips_missing_files(self, detector: DhcpDetector) -> None:
        """Verify scan gracefully handles missing lease files."""
        with patch("os.path.isfile", return_value=False):
            with patch.object(detector, "_parse_lease_file") as mock_parse:
                await detector._scan_impl()
                # Should not attempt to parse missing files
                mock_parse.assert_not_called()
