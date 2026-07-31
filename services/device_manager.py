"""Device Manager — manages device lifecycle with in-memory cache and DB persistence.

Provides fast in-memory access to device state while persisting changes
to the database for durability.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from core.types import MacAddress
from database.engine import get_session_factory
from database.repositories.device import DeviceRepository
from models.device import Device
from models.enums import DeviceStatus

logger = structlog.get_logger(__name__)


class DeviceManager:
    """Manages device CRUD with in-memory caching and database persistence.

    Devices are cached in a thread-safe dictionary for O(1) lookup.
    All mutations are persisted to the database asynchronously.

    Usage:
        manager = DeviceManager()
        device = await manager.get_or_create("AA:BB:CC:DD:EE:FF")
        await manager.save(device)
    """

    def __init__(self) -> None:
        self._cache: dict[MacAddress, Device] = {}
        self._lock = asyncio.Lock()

    async def get(self, mac: MacAddress) -> Device | None:
        """Get a device by MAC address.

        Checks cache first, then falls back to database.

        Args:
            mac: Device MAC address.

        Returns:
            Device entity or None if not found.
        """
        # Check cache
        async with self._lock:
            if mac in self._cache:
                return self._cache[mac]

        # Fall back to database
        factory = get_session_factory()
        async with factory() as session:
            repo = DeviceRepository(session)
            device = await repo.get(mac)
            if device:
                async with self._lock:
                    self._cache[mac] = device
            return device

    async def get_or_create(self, mac: MacAddress) -> Device:
        """Get an existing device or create a new one.

        Args:
            mac: Device MAC address.

        Returns:
            Existing or newly created Device entity.
        """
        device = await self.get(mac)
        if device is not None:
            return device

        device = Device(mac=mac)
        async with self._lock:
            self._cache[mac] = device

        # Persist immediately
        await self.save(device)
        logger.debug("device_created", mac=mac)
        return device

    async def get_by_ip(self, ip: str) -> Device | None:
        """Find a device by IP address.

        Searches the in-memory cache for a device with matching IP.

        Args:
            ip: IP address to search for.

        Returns:
            Device entity or None.
        """
        async with self._lock:
            for device in self._cache.values():
                if device.ip == ip:
                    return device

        # Fall back to database scan (expensive — used only when cache miss)
        factory = get_session_factory()
        async with factory() as session:
            repo = DeviceRepository(session)
            all_devices = await repo.get_all()
            for device in all_devices:
                if device.ip == ip:
                    async with self._lock:
                        self._cache[device.mac] = device
                    return device

        return None

    async def get_all(self) -> list[Device]:
        """Get all cached devices.

        Returns:
            List of all cached Device entities.
        """
        async with self._lock:
            return list(self._cache.values())

    async def get_online(self) -> list[Device]:
        """Get all online devices from cache.

        Returns:
            List of online Device entities.
        """
        async with self._lock:
            return [d for d in self._cache.values() if d.is_online]

    async def save(self, device: Device) -> None:
        """Save a device to cache and database.

        Args:
            device: Device entity to save.
        """
        # Update cache
        async with self._lock:
            self._cache[device.mac] = device

        # Persist to database
        factory = get_session_factory()
        async with factory() as session:
            repo = DeviceRepository(session)
            await repo.upsert(device)
            await session.commit()

    async def delete(self, mac: MacAddress) -> bool:
        """Delete a device from cache and database.

        Args:
            mac: Device MAC address.

        Returns:
            True if the device was deleted, False if not found.
        """
        async with self._lock:
            self._cache.pop(mac, None)

        factory = get_session_factory()
        async with factory() as session:
            repo = DeviceRepository(session)
            if await repo.exists(mac):
                await repo.delete(mac)
                await session.commit()
                logger.debug("device_deleted", mac=mac)
                return True

        return False

    async def load_all_from_db(self) -> int:
        """Load all devices from the database into the cache.

        Used at startup to populate the in-memory cache.

        Returns:
            Number of devices loaded.
        """
        factory = get_session_factory()
        async with factory() as session:
            repo = DeviceRepository(session)
            devices = await repo.get_all()

        async with self._lock:
            for device in devices:
                self._cache[device.mac] = device

        logger.info("devices_loaded_from_db", count=len(devices))
        return len(devices)

    @property
    def cache_size(self) -> int:
        """Number of devices currently in the in-memory cache."""
        return len(self._cache)
