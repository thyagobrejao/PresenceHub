"""Device management API routes.

Provides CRUD endpoints for devices:
    GET    /devices        — list all devices
    GET    /devices/{mac}  — get a single device
    POST   /devices        — create a device
    PUT    /devices/{mac}  — update a device
    DELETE /devices/{mac}  — delete a device
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_device_repo
from api.schemas.device import (
    DeviceCreate,
    DeviceListResponse,
    DeviceResponse,
    DeviceUpdate,
)
from database.repositories.device import DeviceRepository
from models.device import Device
from models.enums import DeviceStatus, DeviceType, OperatingSystem

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=DeviceListResponse)
async def list_devices(
    status_filter: str | None = Query(default=None, alias="status", description="Filter by status (online/offline)"),
    search: str | None = Query(default=None, description="Search by hostname, MAC, or IP"),
    limit: int = Query(default=100, ge=1, le=1000),
    repo: DeviceRepository = Depends(get_device_repo),
) -> DeviceListResponse:
    """List all devices with optional filtering and search.

    Args:
        status_filter: Filter by device status ('online' or 'offline').
        search: Search term for hostname, MAC, or IP.
        limit: Maximum number of devices to return.
        repo: Device repository (injected).

    Returns:
        Paginated device list with counts.
    """
    if status_filter == "online":
        devices = await repo.get_online()
    elif status_filter == "offline":
        devices = await repo.get_offline()
    else:
        devices = await repo.get_all()

    # Apply search filter
    if search:
        search_lower = search.lower()
        devices = [
            d
            for d in devices
            if search_lower in d.hostname.lower()
            or search_lower in d.mac.lower()
            or search_lower in d.ip
        ]

    # Apply limit
    devices = devices[:limit]

    online_count = sum(1 for d in devices if d.is_online)
    offline_count = len(devices) - online_count

    return DeviceListResponse(
        total=len(devices),
        online_count=online_count,
        offline_count=offline_count,
        devices=[_device_to_response(d) for d in devices],
    )


@router.get("/{mac}", response_model=DeviceResponse)
async def get_device(
    mac: str,
    repo: DeviceRepository = Depends(get_device_repo),
) -> DeviceResponse:
    """Get a single device by MAC address.

    Args:
        mac: Device MAC address.
        repo: Device repository (injected).

    Returns:
        Device details.

    Raises:
        HTTPException: 404 if device not found.
    """
    device = await repo.get(mac.upper())
    if not device:
        raise HTTPException(status_code=404, detail=f"Device not found: {mac}")
    return _device_to_response(device)


@router.post("", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_device(
    data: DeviceCreate,
    repo: DeviceRepository = Depends(get_device_repo),
) -> DeviceResponse:
    """Create a new device manually.

    Args:
        data: Device creation data.
        repo: Device repository (injected).

    Returns:
        Created device.

    Raises:
        HTTPException: 409 if device already exists.
    """
    if await repo.exists(data.mac.upper()):
        raise HTTPException(status_code=409, detail=f"Device already exists: {data.mac}")

    device = Device(
        mac=data.mac.upper(),
        hostname=data.hostname,
        ip=data.ip,
        vendor=data.vendor,
        friendly_name=data.friendly_name,
        description=data.description,
        device_type=DeviceType(data.device_type),
        os_type=OperatingSystem(data.os_type),
        ttl=data.ttl,
        status=DeviceStatus.UNKNOWN,
    )

    await repo.add(device)
    return _device_to_response(device)


@router.put("/{mac}", response_model=DeviceResponse)
async def update_device(
    mac: str,
    data: DeviceUpdate,
    repo: DeviceRepository = Depends(get_device_repo),
) -> DeviceResponse:
    """Update an existing device.

    Args:
        mac: Device MAC address.
        data: Fields to update (partial update).
        repo: Device repository (injected).

    Returns:
        Updated device.

    Raises:
        HTTPException: 404 if device not found.
    """
    device = await repo.get(mac.upper())
    if not device:
        raise HTTPException(status_code=404, detail=f"Device not found: {mac}")

    # Apply partial updates
    if data.hostname is not None:
        device.hostname = data.hostname
    if data.ip is not None:
        device.ip = data.ip
    if data.vendor is not None:
        device.vendor = data.vendor
    if data.friendly_name is not None:
        device.friendly_name = data.friendly_name
    if data.description is not None:
        device.description = data.description
    if data.device_type is not None:
        device.device_type = DeviceType(data.device_type)
    if data.os_type is not None:
        device.os_type = OperatingSystem(data.os_type)
    if data.ttl is not None:
        device.ttl = data.ttl

    await repo.update(device)
    return _device_to_response(device)


@router.delete("/{mac}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    mac: str,
    repo: DeviceRepository = Depends(get_device_repo),
) -> None:
    """Delete a device.

    Args:
        mac: Device MAC address.
        repo: Device repository (injected).

    Raises:
        HTTPException: 404 if device not found.
    """
    if not await repo.exists(mac.upper()):
        raise HTTPException(status_code=404, detail=f"Device not found: {mac}")
    await repo.delete(mac.upper())


def _device_to_response(device: Device) -> DeviceResponse:
    """Convert a domain Device to an API response model.

    Args:
        device: Domain Device entity.

    Returns:
        DeviceResponse Pydantic model.
    """
    return DeviceResponse(
        mac=device.mac,
        hostname=device.hostname,
        ip=device.ip,
        vendor=device.vendor,
        first_seen=device.first_seen.isoformat(),
        last_seen=device.last_seen.isoformat(),
        last_source=str(device.last_source),
        confidence=device.confidence,
        status=str(device.status),
        friendly_name=device.friendly_name,
        description=device.description,
        device_type=str(device.device_type),
        os_type=str(device.os_type),
        ttl=device.ttl,
        online=device.is_online,
    )
