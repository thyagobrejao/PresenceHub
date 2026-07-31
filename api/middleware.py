"""FastAPI middleware — CORS, request ID, timing."""

from __future__ import annotations

import time
import uuid

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Adds a unique X-Request-ID header to every response."""

    async def dispatch(self, request: Request, call_next: callable):  # type: ignore[type-arg]
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Logs request method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next: callable):  # type: ignore[type-arg]
        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
        )
        return response


def setup_middleware(app: FastAPI, cors_origins: list[str]) -> None:
    """Configure all middleware for the FastAPI application.

    Args:
        app: FastAPI application instance.
        cors_origins: List of allowed CORS origins.
    """
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID
    app.add_middleware(RequestIDMiddleware)

    # Request timing logging
    app.add_middleware(RequestTimingMiddleware)
