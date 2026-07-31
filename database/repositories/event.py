"""Detection event repository — persists detection history.

Records every detection event for audit trail, history queries, and analytics.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.event import DetectionEventModel
from models.detection import DetectionResult

logger = structlog.get_logger(__name__)


class EventRepository:
    """Async repository for detection event persistence.

    Records every detection from every source for history and audit.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, detection: DetectionResult) -> DetectionEventModel:
        """Record a detection event.

        Args:
            detection: The DetectionResult to persist.

        Returns:
            The persisted DetectionEventModel.
        """
        import json

        event = DetectionEventModel(
            mac=detection.mac,
            ip=detection.ip,
            hostname=detection.hostname,
            source=str(detection.source),
            confidence=detection.confidence,
            vendor=detection.vendor,
            timestamp=detection.timestamp,
            extra_json=json.dumps(detection.extra) if detection.extra else "{}",
        )
        self._session.add(event)
        await self._session.flush()
        return event

    async def get_recent(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get the most recent detection events.

        Args:
            limit: Maximum number of events to return.

        Returns:
            List of detection event dictionaries.
        """
        stmt = select(DetectionEventModel).order_by(DetectionEventModel.timestamp.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return [event.to_dict() for event in result.scalars().all()]

    async def get_by_mac(self, mac: str, limit: int = 50) -> list[dict[str, Any]]:
        """Get detection events for a specific device.

        Args:
            mac: Device MAC address.
            limit: Maximum number of events.

        Returns:
            List of detection event dictionaries.
        """
        stmt = (
            select(DetectionEventModel)
            .where(DetectionEventModel.mac == mac)
            .order_by(DetectionEventModel.timestamp.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [event.to_dict() for event in result.scalars().all()]

    async def get_by_source(self, source: str, limit: int = 50) -> list[dict[str, Any]]:
        """Get detection events from a specific source.

        Args:
            source: Detection source (arp, mdns, ping, etc.).
            limit: Maximum number of events.

        Returns:
            List of detection event dictionaries.
        """
        stmt = (
            select(DetectionEventModel)
            .where(DetectionEventModel.source == source)
            .order_by(DetectionEventModel.timestamp.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [event.to_dict() for event in result.scalars().all()]

    async def cleanup_older_than(self, days: int = 30) -> int:
        """Delete detection events older than the specified number of days.

        Args:
            days: Delete events older than this many days.

        Returns:
            Number of deleted events.
        """
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = select(DetectionEventModel).where(DetectionEventModel.timestamp < cutoff)
        result = await self._session.execute(stmt)
        old_events = result.scalars().all()

        for event in old_events:
            await self._session.delete(event)

        await self._session.flush()
        count = len(old_events)
        if count > 0:
            logger.info("events_cleaned_up", count=count, older_than_days=days)
        return count

    async def count(self) -> int:
        """Get the total number of detection events.

        Returns:
            Total event count.
        """
        stmt = select(func.count()).select_from(DetectionEventModel)
        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    async def get_stats(self) -> dict[str, Any]:
        """Get aggregate event statistics.

        Returns:
            Dictionary with event statistics.
        """
        total = await self.count()

        # Events by source
        stmt = (
            select(DetectionEventModel.source, func.count())
            .group_by(DetectionEventModel.source)
        )
        result = await self._session.execute(stmt)
        by_source = {row[0]: row[1] for row in result.all()}

        return {
            "total_events": total,
            "events_by_source": by_source,
        }
