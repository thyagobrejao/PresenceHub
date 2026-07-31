"""Unit tests for Home Assistant MQTT Discovery."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from core.bus import AsyncioEventBus
from core.events import EventType
from models.device import Device
from mqtt.client import MqttClient
from mqtt.discovery import HADiscovery


class TestHADiscovery:
    """Tests for HADiscovery module."""

    @pytest.fixture
    def mock_client(self, config, event_bus) -> MqttClient:
        """Create a mock MQTT client."""
        client = MqttClient(config, event_bus)
        client._connected = True
        client.publish = AsyncMock()  # type: ignore[method-assign]
        return client

    @pytest.fixture
    def discovery(self, mock_client: MqttClient, event_bus: AsyncioEventBus) -> HADiscovery:
        return HADiscovery(mock_client, event_bus, discovery_prefix="homeassistant")

    @pytest.mark.unit
    async def test_publish_discovery(self, discovery: HADiscovery, mock_client: MqttClient) -> None:
        """Verify discovery publishes binary_sensor and device_tracker configs."""
        device = Device(
            mac="AA:BB:CC:DD:EE:FF",
            hostname="myphone",
            ip="192.168.1.100",
            vendor="Apple",
        )

        await discovery.publish_discovery(device)

        # Should publish 2 discovery messages (binary_sensor + device_tracker)
        assert mock_client.publish.call_count == 2  # type: ignore[union-attr]

    @pytest.mark.unit
    async def test_publish_discovery_idempotent(self, discovery: HADiscovery, mock_client: MqttClient) -> None:
        """Verify discovery is idempotent — only publishes once per device."""
        device = Device(mac="AA:BB:CC:DD:EE:FF", hostname="test", ip="192.168.1.1")

        await discovery.publish_discovery(device)
        assert mock_client.publish.call_count == 2  # type: ignore[union-attr]

        # Second call should not publish again
        await discovery.publish_discovery(device)
        assert mock_client.publish.call_count == 2  # type: ignore[union-attr]

    @pytest.mark.unit
    async def test_remove_discovery(self, discovery: HADiscovery, mock_client: MqttClient) -> None:
        """Verify removal publishes empty config messages."""
        device = Device(mac="AA:BB:CC:DD:EE:FF", hostname="test", ip="192.168.1.1")

        await discovery.publish_discovery(device)
        await discovery.remove_discovery(device.mac)

        # 2 for discovery + 2 for removal = 4
        assert mock_client.publish.call_count == 4  # type: ignore[union-attr]

    @pytest.mark.unit
    async def test_on_device_detected_triggers_discovery(
        self, discovery: HADiscovery, event_bus: AsyncioEventBus, mock_client: MqttClient
    ) -> None:
        """Verify that DEVICE_DETECTED event triggers discovery."""
        discovery.subscribe()

        await event_bus.publish(
            EventType.DEVICE_DETECTED,
            {
                "mac": "AA:BB:CC:DD:EE:FF",
                "ip": "192.168.1.100",
                "hostname": "myphone",
                "vendor": "Apple",
                "source": "arp",
                "confidence": 100,
            },
        )

        # Should have published discovery
        assert mock_client.publish.call_count >= 2  # type: ignore[union-attr]

    @pytest.mark.unit
    async def test_on_device_detected_no_mac(self, discovery: HADiscovery, mock_client: MqttClient) -> None:
        """Verify that detection without MAC is ignored."""
        discovery.subscribe()

        # Reset mock
        mock_client.publish.reset_mock()  # type: ignore[union-attr]

        # Event with no MAC should not trigger discovery
        # (handled internally by _on_device_detected which checks for mac)
        await discovery._on_device_detected({"ip": "192.168.1.100"})

        # Should not have published anything
        assert mock_client.publish.call_count == 0  # type: ignore[union-attr]
