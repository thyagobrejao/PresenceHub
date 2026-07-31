"""API route modules."""

from api.routes.devices import router as devices_router
from api.routes.health import router as health_router
from api.routes.history import router as history_router
from api.routes.metrics import router as metrics_router
from api.routes.stats import router as stats_router

__all__ = [
    "devices_router",
    "health_router",
    "history_router",
    "metrics_router",
    "stats_router",
]
