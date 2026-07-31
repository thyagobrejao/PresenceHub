"""History API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from api.dependencies import get_event_repo
from database.repositories.event import EventRepository

router = APIRouter(prefix="/history", tags=["history"])


@router.get("")
async def get_history(
    mac: str | None = Query(default=None, description="Filter by MAC address"),
    source: str | None = Query(default=None, description="Filter by detection source"),
    limit: int = Query(default=100, ge=1, le=1000),
    repo: EventRepository = Depends(get_event_repo),
) -> list[dict[str, Any]]:
    """Get detection event history.

    Args:
        mac: Optional MAC address filter.
        source: Optional detection source filter.
        limit: Maximum number of events.
        repo: Event repository (injected).

    Returns:
        List of detection events.
    """
    if mac:
        return await repo.get_by_mac(mac.upper(), limit=limit)
    if source:
        return await repo.get_by_source(source, limit=limit)
    return await repo.get_recent(limit=limit)
