"""Repository implementations for data access.

Following the Repository pattern to abstract database operations
behind clean interfaces.
"""

from database.repositories.device import DeviceRepository
from database.repositories.event import EventRepository

__all__ = [
    "DeviceRepository",
    "EventRepository",
]
