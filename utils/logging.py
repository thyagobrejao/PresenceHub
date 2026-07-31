"""Structured logging configuration using structlog.

Provides JSON-formatted logs for production and colored console output for development.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from rich.console import Console
from structlog.typing import EventDict, Processor


def _drop_color_message_key(_, __, event_dict: EventDict) -> EventDict:
    """Remove the color_message key used by Rich rendering."""
    event_dict.pop("color_message", None)
    return event_dict


def _add_process_id(_: Any, __: Any, event_dict: EventDict) -> EventDict:
    """Add the process ID to the event dictionary."""
    import os

    event_dict["pid"] = os.getpid()
    return event_dict


def configure_logging(
    level: str = "INFO",
    json_format: bool = True,
    render_console: bool = False,
) -> None:
    """Configure structlog for the entire application.

    In production (json_format=True), logs are emitted as JSON lines to stdout.
    In development (render_console=True), Rich-powered colored console output is used.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
        json_format: Whether to output JSON-formatted logs.
        render_console: Whether to render colored console output via Rich.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Shared processors applied to all renderers
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        _add_process_id,
    ]

    if render_console:
        # Development: Rich-powered colored console output
        console = Console(file=sys.stderr)
        structlog.configure(
            processors=[
                *shared_processors,
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
            cache_logger_on_first_use=True,
        )
    elif json_format:
        # Production: JSON output to stdout
        structlog.configure(
            processors=[
                *shared_processors,
                _drop_color_message_key,
                structlog.processors.dict_tracebacks,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Plain text fallback
        structlog.configure(
            processors=[
                *shared_processors,
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
            cache_logger_on_first_use=True,
        )

    # Silence noisy third-party loggers
    logging.getLogger("aiomqtt").setLevel(logging.WARNING)
    logging.getLogger("scapy").setLevel(logging.WARNING)
    logging.getLogger("zeroconf").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logger = structlog.get_logger(__name__)
    logger.info("logging_configured", level=level, json_format=json_format)


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """Get a structlog logger instance.

    Args:
        name: Logger name (typically __name__ from the calling module).

    Returns:
        A bound structlog logger.
    """
    return structlog.get_logger(name)
