"""Health check API routes.

Provides liveness and readiness probes for Kubernetes/Docker health checks.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["health"])

_start_time = datetime.now(timezone.utc)


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Liveness check — always returns OK if the server is running.

    Returns:
        Health status dictionary.
    """
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/health/ready")
async def readiness_check() -> dict[str, Any]:
    """Readiness check — returns OK when the app is ready to serve.

    Returns:
        Readiness status dictionary with uptime.
    """
    uptime = (datetime.now(timezone.utc) - _start_time).total_seconds()
    return {
        "status": "ready",
        "uptime_seconds": uptime,
        "started_at": _start_time.isoformat(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
