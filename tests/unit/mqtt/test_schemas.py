"""Unit tests for MQTT schemas."""

from __future__ import annotations

import pytest

from models.device import Device
from models.enums import DeviceStatus, DeviceType
from mqtt.schemas import (
    device_presence_payload,
    ha_binary_sensor_discovery,
    ha_device_tracker_discovery,
    online_payload,
)


class TestMqttSchemas:
    """Tests for MQTT payload schemas."""

    @pytest.fixture
    def device_online(self) -> Device:
        return Device(
            mac="AA:BB:CC:DD:EE:FF",
            hostname="myphone",
            ip="192.168.1.100",
            vendor="Apple",
            status=DeviceStatus.ONLINE,
            confidence=100,
            device_type=DeviceType.PHONE,
            friendly_name="Thyago's Phone",
        )

    @pytest.fixture
    def device_offline(self) -> Device:
        return Device(
            mac="11:22:33:44:55:66",
            hostname="laptop",
            ip="192.168.1.101",
            vendor="Dell",
            status=DeviceStatus.OFFLINE,
            confidence=0,
            device_type=DeviceType.LAPTOP,
        )

    @pytest.mark.unit
    def test_online_payload(self, device_online: Device) -> None:
        """Verify online payload returns 'online'."""
        assert online_payload(device_online) == "online"

    @pytest.mark.unit
    def test_offline_payload(self, device_offline: Device) -> None:
        """Verify offline payload returns 'offline'."""
        assert online_payload(device_offline) == "offline"

    @pytest.mark.unit
    def test_device_presence_payload_online(self, device_online: Device) -> None:
        """Verify full JSON payload for online device."""
        payload = device_presence_payload(device_online)
        assert payload["name"] == "Thyago's Phone"
        assert payload["online"] is True
        assert payload["mac"] == "AA:BB:CC:DD:EE:FF"
        assert payload["ip"] == "192.168.1.100"
        assert payload["confidence"] == 100
        assert payload["vendor"] == "Apple"
        assert "last_seen" in payload
        assert "last_source" in payload

    @pytest.mark.unit
    def test_device_presence_payload_offline(self, device_offline: Device) -> None:
        """Verify full JSON payload for offline device."""
        payload = device_presence_payload(device_offline)
        assert payload["online"] is False
        assert payload["confidence"] == 0
        assert payload["name"] == "laptop"

    @pytest.mark.unit
    def test_ha_binary_sensor_discovery(self, device_online: Device) -> None:
        """Verify HA binary_sensor discovery payload."""
        topic, payload = ha_binary_sensor_discovery(
            device_online,
            topic_prefix="home/presence",
            discovery_prefix="homeassistant",
        )

        assert topic == "homeassistant/binary_sensor/presence_aa_bb_cc_dd_ee_ff/config"
        assert payload["name"] == "Thyago's Phone"
        assert payload["device_class"] == "presence"
        assert payload["state_topic"] == "home/presence/AA:BB:CC:DD:EE:FF/status"
        assert payload["icon"] == "mdi:cellphone"
        assert payload["payload_on"] == "online"
        assert payload["payload_off"] == "offline"
        assert "device" in payload
        assert payload["device"]["manufacturer"] == "Apple"

    @pytest.mark.unit
    def test_ha_device_tracker_discovery(self, device_offline: Device) -> None:
        """Verify HA device_tracker discovery payload."""
        topic, payload = ha_device_tracker_discovery(
            device_offline,
            topic_prefix="home/presence",
            discovery_prefix="homeassistant",
        )

        assert topic == "homeassistant/device_tracker/tracker_11_22_33_44_55_66/config"
        assert payload["source_type"] == "router"
        assert payload["icon"] == "mdi:map-marker"
        assert payload["state_topic"] == "home/presence/11:22:33:44:55:66/status"

    @pytest.mark.unit
    def test_device_fallback_name(self) -> None:
        """Verify fallback name when friendly_name is empty."""
        device = Device(
            mac="AA:BB:CC:DD:EE:FF",
            hostname="unknown-device",
        )
        payload = device_presence_payload(device)
        assert payload["name"] == "unknown-device"
