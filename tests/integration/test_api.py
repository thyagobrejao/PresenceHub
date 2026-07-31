"""Integration tests for the FastAPI REST API."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from api.app import create_app
from config.loader import ConfigLoader
from database.engine import init_database


class TestAPI:
    """Integration tests for the REST API."""

    @pytest.fixture
    async def client(self) -> AsyncClient:
        """Create a test HTTP client with temporary file-based database."""
        import tempfile
        import os

        from database.engine import close_database

        # Use temp file for SQLite so all connections share the same DB
        fd, db_path = tempfile.mkstemp(suffix=".db", prefix="presencehub_test_")
        os.close(fd)

        await init_database(
            f"sqlite+aiosqlite:///{db_path}",
            echo=False,
        )

        config = ConfigLoader.load(None)
        app = create_app(config)
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

        # Cleanup
        await close_database()
        try:
            os.unlink(db_path)
        except OSError:
            pass

    @pytest.mark.integration
    async def test_health_check(self, client: AsyncClient) -> None:
        """Verify health endpoint returns OK."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data

    @pytest.mark.integration
    async def test_readiness_check(self, client: AsyncClient) -> None:
        """Verify readiness endpoint returns ready."""
        response = await client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "uptime_seconds" in data

    @pytest.mark.integration
    async def test_metrics_endpoint(self, client: AsyncClient) -> None:
        """Verify Prometheus metrics endpoint."""
        response = await client.get("/metrics")
        assert response.status_code == 200
        assert "presencehub" in response.text

    @pytest.mark.integration
    async def test_list_devices_empty(self, client: AsyncClient) -> None:
        """Verify listing devices when empty."""
        response = await client.get("/devices")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["devices"] == []

    @pytest.mark.integration
    async def test_create_and_get_device(self, client: AsyncClient) -> None:
        """Verify creating and retrieving a device."""
        # Create
        create_data = {
            "mac": "AA:BB:CC:DD:EE:FF",
            "hostname": "test-device",
            "ip": "192.168.1.100",
            "vendor": "TestCorp",
            "friendly_name": "Test Device",
        }
        response = await client.post("/devices", json=create_data)
        assert response.status_code == 201
        created = response.json()
        assert created["mac"] == "AA:BB:CC:DD:EE:FF"
        assert created["hostname"] == "test-device"

        # Get by MAC
        response = await client.get("/devices/AA:BB:CC:DD:EE:FF")
        assert response.status_code == 200
        fetched = response.json()
        assert fetched["mac"] == "AA:BB:CC:DD:EE:FF"

    @pytest.mark.integration
    async def test_create_duplicate_device(self, client: AsyncClient) -> None:
        """Verify duplicate device creation returns 409."""
        create_data = {
            "mac": "11:22:33:44:55:66",
            "hostname": "dup-device",
            "ip": "192.168.1.200",
        }
        response = await client.post("/devices", json=create_data)
        assert response.status_code == 201

        response = await client.post("/devices", json=create_data)
        assert response.status_code == 409

    @pytest.mark.integration
    async def test_update_device(self, client: AsyncClient) -> None:
        """Verify updating a device."""
        # Create first
        await client.post("/devices", json={
            "mac": "AA:BB:CC:DD:EE:11",
            "hostname": "old-name",
            "ip": "192.168.1.50",
        })

        # Update
        response = await client.put("/devices/AA:BB:CC:DD:EE:11", json={
            "hostname": "new-name",
            "friendly_name": "Updated Device",
        })
        assert response.status_code == 200
        updated = response.json()
        assert updated["hostname"] == "new-name"
        assert updated["friendly_name"] == "Updated Device"

    @pytest.mark.integration
    async def test_delete_device(self, client: AsyncClient) -> None:
        """Verify deleting a device."""
        await client.post("/devices", json={
            "mac": "AA:BB:CC:DD:EE:22",
            "hostname": "to-delete",
            "ip": "192.168.1.99",
        })

        response = await client.delete("/devices/AA:BB:CC:DD:EE:22")
        assert response.status_code == 204

        # Verify deleted
        response = await client.get("/devices/AA:BB:CC:DD:EE:22")
        assert response.status_code == 404

    @pytest.mark.integration
    async def test_get_nonexistent_device(self, client: AsyncClient) -> None:
        """Verify getting a nonexistent device returns 404."""
        response = await client.get("/devices/FF:FF:FF:FF:FF:FF")
        assert response.status_code == 404

    @pytest.mark.integration
    async def test_stats_endpoint(self, client: AsyncClient) -> None:
        """Verify stats endpoint returns aggregate data."""
        response = await client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_devices" in data
        assert "online_devices" in data
        assert "total_events" in data

    @pytest.mark.integration
    async def test_history_endpoint(self, client: AsyncClient) -> None:
        """Verify history endpoint."""
        response = await client.get("/history")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
