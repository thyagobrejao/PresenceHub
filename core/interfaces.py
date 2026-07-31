"""Abstract interfaces for the PresenceHub system.

All core abstractions are defined here following the Interface Segregation Principle.
Detectors, event subscribers, and other components must implement these interfaces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from typing import Any

from core.types import EventPayload


# --- Detector Interface ---

class PresenceDetector(ABC):
    """Abstract interface for all presence detectors.

    Each detector (ARP, mDNS, Ping, DHCP, etc.) must implement this interface.
    Detectors are started/stopped by the PresenceEngine and publish detection
    results to the internal EventBus.

    Lifecycle:
        1. __init__(config, bus) — injected dependencies
        2. start() — begin detection loop
        3. [detection events published to bus]
        4. stop() — graceful shutdown
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable detector name (e.g., 'arp', 'mdns', 'ping')."""
        ...

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Whether the detector is currently active."""
        ...

    @abstractmethod
    async def start(self) -> None:
        """Start the detection process.

        This method should initiate the detector's main loop and return
        immediately (non-blocking). Detection results are published to
        the EventBus asynchronously.
        """
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the detection process gracefully.

        Should cancel any running tasks, close connections, and clean up resources.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check whether the detector is healthy and operational.

        Returns:
            True if the detector is functioning correctly.
        """
        ...


# --- Event Bus Interface ---

type EventHandler = Callable[[EventPayload], Coroutine[Any, Any, None]]
"""Async callback signature for event handlers: async def handler(payload: EventPayload) -> None"""


class EventBus(ABC):
    """Abstract interface for the internal EventBus.

    Implements a publish/subscribe pattern for decoupled communication
    between detectors, services, and other components.
    """

    @abstractmethod
    async def publish(self, event_type: str, payload: EventPayload) -> None:
        """Publish an event to all registered subscribers.

        Args:
            event_type: The event type identifier (e.g., 'device.detected').
            payload: Event-specific data dictionary.
        """
        ...

    @abstractmethod
    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register a handler for a specific event type.

        Args:
            event_type: The event type to subscribe to.
            handler: Async callback invoked when the event is published.
        """
        ...

    @abstractmethod
    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remove a handler registration.

        Args:
            event_type: The event type to unsubscribe from.
            handler: The handler to remove.
        """
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """Gracefully shut down the event bus, draining pending events."""
        ...


# --- Repository Interface ---

from typing import Protocol, TypeVar

T = TypeVar("T")


class Repository(Protocol[T]):
    """Generic repository protocol for data access abstraction."""

    async def get(self, id: str) -> T | None: ...  # noqa: A002

    async def get_all(self) -> list[T]: ...

    async def add(self, entity: T) -> T: ...

    async def update(self, entity: T) -> T: ...

    async def delete(self, id: str) -> None: ...  # noqa: A002

    async def exists(self, id: str) -> bool: ...  # noqa: A002
