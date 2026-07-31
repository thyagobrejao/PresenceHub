"""Asynchronous EventBus implementation.

Provides the concrete implementation of the EventBus interface using asyncio.
Supports multiple subscribers per event type, graceful shutdown, and error isolation
(one failing handler does not affect others).
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any

import structlog

from core.events import EventType
from core.exceptions import EventHandlerError
from core.interfaces import EventBus, EventHandler
from core.types import EventPayload

logger = structlog.get_logger(__name__)


class AsyncioEventBus(EventBus):
    """Asyncio-based EventBus implementation.

    Features:
        - Multiple subscribers per event type
        - Handlers are invoked concurrently via asyncio.gather
        - Error isolation: one failing handler does not affect others
        - Graceful shutdown with draining

    Usage:
        bus = AsyncioEventBus()
        bus.subscribe(EventType.DEVICE_DETECTED, my_handler)
        await bus.publish(EventType.DEVICE_DETECTED, {"mac": "AA:BB:CC:DD:EE:FF"})
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._pending_tasks: set[asyncio.Task[None]] = set()
        self._lock = asyncio.Lock()
        self._shutting_down = False

    def subscribe(self, event_type: str | EventType, handler: EventHandler) -> None:
        """Register a handler for a specific event type.

        Args:
            event_type: The event type to subscribe to.
            handler: Async callback invoked when the event is published.
        """
        event_type_str = str(event_type)
        self._subscribers[event_type_str].append(handler)
        logger.debug("event_subscribed", event_type=event_type_str, handler=handler.__name__)

    def unsubscribe(self, event_type: str | EventType, handler: EventHandler) -> None:
        """Remove a handler registration.

        Args:
            event_type: The event type to unsubscribe from.
            handler: The handler to remove.
        """
        event_type_str = str(event_type)
        try:
            self._subscribers[event_type_str].remove(handler)
            logger.debug("event_unsubscribed", event_type=event_type_str, handler=handler.__name__)
        except ValueError:
            logger.warning("event_unsubscribe_not_found", event_type=event_type_str, handler=handler.__name__)

    async def publish(self, event_type: str | EventType, payload: EventPayload) -> None:
        """Publish an event to all registered subscribers.

        Handlers are invoked concurrently via asyncio.gather.
        If a handler raises an exception, it is logged and the remaining
        handlers continue execution.

        Args:
            event_type: The event type identifier.
            payload: Event-specific data dictionary.
        """
        if self._shutting_down:
            logger.debug("event_dropped_shutting_down", event_type=str(event_type))
            return

        event_type_str = str(event_type)
        subscribers = self._subscribers.get(event_type_str, [])

        if not subscribers:
            logger.debug("event_no_subscribers", event_type=event_type_str)
            return

        logger.debug("event_publishing", event_type=event_type_str, subscriber_count=len(subscribers))

        # Create tasks for all handlers
        async with self._lock:
            tasks = []
            for handler in subscribers:
                task = asyncio.create_task(self._safe_invoke(handler, event_type_str, payload))
                self._pending_tasks.add(task)
                task.add_done_callback(self._pending_tasks.discard)
                tasks.append(task)

        # Await all handler tasks to ensure they complete before returning
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_invoke(self, handler: EventHandler, event_type: str, payload: EventPayload) -> None:
        """Invoke a handler safely, logging any exceptions.

        Args:
            handler: The handler to invoke.
            event_type: The event type (for logging).
            payload: The event payload.
        """
        try:
            await handler(payload)
        except Exception as exc:
            logger.error(
                "event_handler_error",
                event_type=event_type,
                handler=handler.__name__,
                error=str(exc),
                exc_info=True,
            )
            # Do not re-raise — one failing handler must not break others

    async def shutdown(self) -> None:
        """Gracefully shut down the event bus.

        Sets the shutdown flag and waits for all pending handler tasks to complete.
        """
        self._shutting_down = True
        logger.info("event_bus_shutting_down", pending_tasks=len(self._pending_tasks))

        if self._pending_tasks:
            await asyncio.gather(*self._pending_tasks, return_exceptions=True)

        logger.info("event_bus_shutdown_complete")
