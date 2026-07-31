"""Confidence Decay Background Worker.

Runs periodically to apply confidence decay to all tracked devices,
transitioning stale devices to offline.
"""

from __future__ import annotations

import asyncio

import structlog

from services.presence import PresenceEngine

logger = structlog.get_logger(__name__)


class DecayWorker:
    """Background worker that periodically applies confidence decay.

    Runs as an asyncio task, calling PresenceEngine.apply_decay_cycle()
    at the configured interval.

    Usage:
        worker = DecayWorker(engine, interval=60)
        await worker.start()
        # ... application runs ...
        await worker.stop()
    """

    def __init__(self, engine: PresenceEngine, interval: int = 60) -> None:
        """Initialize the decay worker.

        Args:
            engine: The PresenceEngine instance.
            interval: Decay cycle interval in seconds.
        """
        self._engine = engine
        self._interval = interval
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self) -> None:
        """Start the decay worker as a background task."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._loop(), name="decay-worker")
        logger.info("decay_worker_started", interval=self._interval)

    async def stop(self) -> None:
        """Stop the decay worker gracefully."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("decay_worker_stopped")

    async def _loop(self) -> None:
        """Main decay loop."""
        while self._running:
            try:
                await asyncio.sleep(self._interval)
                if not self._running:
                    break
                await self._engine.apply_decay_cycle()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("decay_cycle_error")
