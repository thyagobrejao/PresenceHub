"""Stats API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from api.dependencies import get_device_repo, get_event_repo
from database.repositories.device import DeviceRepository
from database.repositories.event import EventRepository

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
async def get_stats(
    device_repo: DeviceRepository = Depends(get_device_repo),
    event_repo: EventRepository = Depends(get_event_repo),
) -> dict[str, Any]:
    """Get aggregate statistics.

    Returns:
        Dictionary with device and event statistics.
    """
    device_stats = await device_repo.get_stats()
    event_stats = await event_repo.get_stats()

    return {
        **device_stats,
        **event_stats,
    }
