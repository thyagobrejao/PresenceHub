"""Stats API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

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


@router.get("/mqtt")
async def get_mqtt_status(request: Request) -> dict[str, Any]:
    """Get MQTT broker connection status and details.

    Returns:
        MQTT status dictionary with connected, host, port, topic_prefix.
    """
    mqtt_client = getattr(request.app.state, "mqtt_client", None)
    if not mqtt_client:
        return {
            "connected": False,
            "host": "N/A",
            "port": 0,
            "topic_prefix": "home/presence",
        }
    return {
        "connected": mqtt_client.is_connected,
        "host": getattr(mqtt_client, "_host", "localhost"),
        "port": getattr(mqtt_client, "_port", 1883),
        "topic_prefix": getattr(mqtt_client, "topic_prefix", "home/presence"),
    }
