"""Device repository — async data access for the devices table.

Implements CRUD operations and domain-model ↔ ORM-model conversion.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.types import ConfidenceValue, Hostname, IPv4Address, MacAddress
from database.models.device import DeviceModel
from models.device import Device
from models.enums import DetectionSource, DeviceStatus, DeviceType, OperatingSystem

logger = structlog.get_logger(__name__)


def _orm_to_domain(orm: DeviceModel) -> Device:
    """Convert an ORM model to a domain Device entity.

    Args:
        orm: The SQLAlchemy ORM model instance.

    Returns:
        A domain Device entity.
    """
    extra: dict[str, str] = {}
    try:
        extra = json.loads(orm.extra_json)
    except (json.JSONDecodeError, TypeError):
        pass

    return Device(
        mac=MacAddress(orm.mac),
        hostname=Hostname(orm.hostname),
        ip=IPv4Address(orm.ip),
        vendor=orm.vendor,
        first_seen=orm.first_seen,
        last_seen=orm.last_seen,
        last_source=DetectionSource(orm.last_source),
        confidence=ConfidenceValue(orm.confidence),
        status=DeviceStatus(orm.status),
        friendly_name=orm.friendly_name,
        description=orm.description,
        device_type=DeviceType(orm.device_type),
        os_type=OperatingSystem(orm.os_type),
        ttl=orm.ttl,
        extra=extra,
    )


def _domain_to_orm(device: Device, existing: DeviceModel | None = None) -> DeviceModel:
    """Convert a domain Device entity to an ORM model.

    Args:
        device: The domain Device entity.
        existing: An existing ORM model to update, or None to create new.

    Returns:
        A DeviceModel ready for persistence.
    """
    orm = existing or DeviceModel()
    orm.mac = device.mac
    orm.hostname = device.hostname
    orm.ip = device.ip
    orm.vendor = device.vendor
    orm.first_seen = device.first_seen
    orm.last_seen = device.last_seen
    orm.last_source = str(device.last_source)
    orm.confidence = device.confidence
    orm.status = str(device.status)
    orm.friendly_name = device.friendly_name
    orm.description = device.description
    orm.device_type = str(device.device_type)
    orm.os_type = str(device.os_type)
    orm.ttl = device.ttl
    orm.extra_json = json.dumps(device.extra) if device.extra else "{}"
    return orm


class DeviceRepository:
    """Async repository for Device persistence.

    Provides full CRUD operations with domain/ORM model conversion.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, mac: str) -> Device | None:
        """Get a device by MAC address.

        Args:
            mac: The device MAC address.

        Returns:
            The Device entity, or None if not found.
        """
        stmt = select(DeviceModel).where(DeviceModel.mac == mac)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _orm_to_domain(orm) if orm else None

    async def get_all(self) -> list[Device]:
        """Get all devices.

        Returns:
            List of all Device entities.
        """
        stmt = select(DeviceModel).order_by(DeviceModel.last_seen.desc())
        result = await self._session.execute(stmt)
        return [_orm_to_domain(orm) for orm in result.scalars().all()]

    async def get_online(self) -> list[Device]:
        """Get all online devices.

        Returns:
            List of online Device entities.
        """
        stmt = (
            select(DeviceModel)
            .where(DeviceModel.status == "online")
            .order_by(DeviceModel.last_seen.desc())
        )
        result = await self._session.execute(stmt)
        return [_orm_to_domain(orm) for orm in result.scalars().all()]

    async def get_offline(self) -> list[Device]:
        """Get all offline devices.

        Returns:
            List of offline Device entities.
        """
        stmt = (
            select(DeviceModel)
            .where(DeviceModel.status == "offline")
            .order_by(DeviceModel.last_seen.desc())
        )
        result = await self._session.execute(stmt)
        return [_orm_to_domain(orm) for orm in result.scalars().all()]

    async def add(self, device: Device) -> Device:
        """Add a new device.

        Args:
            device: The Device entity to add.

        Returns:
            The added Device entity.
        """
        orm = _domain_to_orm(device)
        self._session.add(orm)
        await self._session.flush()
        logger.debug("device_added", mac=device.mac)
        return device

    async def update(self, device: Device) -> Device:
        """Update an existing device.

        Args:
            device: The Device entity with updated fields.

        Returns:
            The updated Device entity.
        """
        stmt = select(DeviceModel).where(DeviceModel.mac == device.mac)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is None:
            # Fall back to insert if not found
            return await self.add(device)

        _domain_to_orm(device, existing)
        await self._session.flush()
        logger.debug("device_updated", mac=device.mac)
        return device

    async def upsert(self, device: Device) -> Device:
        """Insert or update a device (upsert).

        Args:
            device: The Device entity to upsert.

        Returns:
            The upserted Device entity.
        """
        stmt = select(DeviceModel).where(DeviceModel.mac == device.mac)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            _domain_to_orm(device, existing)
        else:
            orm = _domain_to_orm(device)
            self._session.add(orm)

        await self._session.flush()
        return device

    async def delete(self, mac: str) -> None:
        """Delete a device by MAC address.

        Args:
            mac: The device MAC address.
        """
        stmt = select(DeviceModel).where(DeviceModel.mac == mac)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            await self._session.delete(orm)
            await self._session.flush()
            logger.debug("device_deleted", mac=mac)

    async def exists(self, mac: str) -> bool:
        """Check if a device exists.

        Args:
            mac: The device MAC address.

        Returns:
            True if the device exists.
        """
        stmt = select(DeviceModel).where(DeviceModel.mac == mac)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_stale_devices(self, timeout_seconds: int) -> list[Device]:
        """Get devices that haven't been seen within the timeout period.

        Args:
            timeout_seconds: Stale threshold in seconds.

        Returns:
            List of stale Device entities.
        """
        cutoff = datetime.now(timezone.utc).timestamp() - timeout_seconds
        cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc)
        stmt = (
            select(DeviceModel)
            .where(DeviceModel.last_seen < cutoff_dt)
            .where(DeviceModel.status == "online")
        )
        result = await self._session.execute(stmt)
        return [_orm_to_domain(orm) for orm in result.scalars().all()]

    async def count(self) -> int:
        """Get the total number of devices.

        Returns:
            Device count.
        """
        from sqlalchemy import func

        stmt = select(func.count()).select_from(DeviceModel)
        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    async def count_online(self) -> int:
        """Get the number of online devices.

        Returns:
            Online device count.
        """
        from sqlalchemy import func

        stmt = select(func.count()).select_from(DeviceModel).where(DeviceModel.status == "online")
        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    async def get_stats(self) -> dict[str, Any]:
        """Get aggregate device statistics.

        Returns:
            Dictionary with device statistics.
        """
        total = await self.count()
        online = await self.count_online()
        return {
            "total_devices": total,
            "online_devices": online,
            "offline_devices": total - online,
        }
