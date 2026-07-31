"""Prometheus metrics endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, generate_latest

router = APIRouter(tags=["metrics"])

# Prometheus metrics registry
registry = CollectorRegistry()

# Metrics
devices_total = Gauge(
    "presencehub_devices_total",
    "Total number of tracked devices",
    registry=registry,
)

devices_online = Gauge(
    "presencehub_devices_online",
    "Number of online devices",
    registry=registry,
)

detections_total = Counter(
    "presencehub_detections_total",
    "Total number of detection events",
    ["source"],
    registry=registry,
)

uptime_seconds = Gauge(
    "presencehub_uptime_seconds",
    "Service uptime in seconds",
    registry=registry,
)


@router.get("/metrics")
async def get_metrics() -> Response:
    """Prometheus metrics endpoint.

    Returns:
        Plain text response with Prometheus metrics.
    """
    return Response(
        content=generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST,
    )
