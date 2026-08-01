"""FastAPI application factory for PresenceHub.

Creates and configures the FastAPI application with all routes,
middleware, and lifecycle handlers.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from api.middleware import setup_middleware
from api.routes import (
    devices_router,
    health_router,
    history_router,
    metrics_router,
    stats_router,
)
from config.loader import ConfigLoader
from core.bus import AsyncioEventBus
from detectors.registry import DetectorRegistry
from mqtt.client import MqttClient
from mqtt.discovery import HADiscovery
from mqtt.publisher import MqttPublisher
from models.enums import DeviceStatus, DetectionSource
from services.confidence import ConfidenceCalculator
from services.device_manager import DeviceManager
from services.presence import PresenceEngine
from workers.decay import DecayWorker

# Module-level reference to the config (set during create_app)
_app_config: ConfigLoader | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:  # type: ignore[type-arg]
    """Application lifespan handler — startup and shutdown.

    Initializes and starts all detection components:
        - EventBus for internal event routing
        - DeviceManager for device state persistence
        - ConfidenceCalculator for scoring
        - PresenceEngine for detection pipeline
        - DetectorRegistry for network scanners
        - MqttClient + MqttPublisher for Home Assistant integration
        - DecayWorker for confidence decay
    """
    import structlog

    logger = structlog.get_logger(__name__)
    logger.info("api_starting")

    # Get config from app state (set in create_app)
    config = app.state.config

    # 1. Create the EventBus
    bus = AsyncioEventBus()

    # 2. Create DeviceManager and load existing devices from DB
    device_manager = DeviceManager()
    await device_manager.load_all_from_db()

    # 3. Create ConfidenceCalculator with config values
    online_threshold = config.get("presence", "online_threshold", default=50)
    decay_rate = config.get("presence", "decay_rate", default=5)
    timeout = config.get("presence", "timeout", default=300)
    confidence = ConfidenceCalculator(
        online_threshold=online_threshold,
        decay_rate=decay_rate,
        default_ttl=timeout,
    )

    # Initialize online devices in the confidence calculator so their status can decay
    for device in await device_manager.get_all():
        if device.status == DeviceStatus.ONLINE:
            confidence.process_detection(
                mac=device.mac,
                source=DetectionSource.ARP,  # Use ARP to start at 100 points
                ip=device.ip,
                hostname=device.hostname,
                vendor=device.vendor,
            )

    # 4. Create and subscribe PresenceEngine
    engine = PresenceEngine(bus, device_manager, confidence)
    engine.subscribe()

    # 5. Create and start MQTT client + publisher + HA Discovery
    mqtt_client = MqttClient(config, bus)
    mqtt_publisher = MqttPublisher(mqtt_client, bus, device_manager)
    mqtt_publisher.subscribe()

    ha_discovery_enabled = config.get("home_assistant", "discovery_enabled", default=True)
    if ha_discovery_enabled:
        discovery_prefix = config.get("home_assistant", "discovery_prefix", default="homeassistant")
        ha_discovery = HADiscovery(mqtt_client, bus, device_manager, discovery_prefix)
        ha_discovery.subscribe()

    await mqtt_client.connect()

    # 6. Create and start DetectorRegistry
    registry = DetectorRegistry(config, bus)
    registry.load_enabled()
    await registry.start_all()

    # 7. Create and start DecayWorker
    decay_interval = config.get("presence", "decay_interval", default=60)
    decay_worker = DecayWorker(engine, interval=decay_interval)
    await decay_worker.start()

    # Store references on app.state for API routes to access
    app.state.bus = bus
    app.state.device_manager = device_manager
    app.state.registry = registry
    app.state.mqtt_client = mqtt_client

    logger.info("all_components_started")

    yield

    # Shutdown
    logger.info("api_shutting_down")
    await decay_worker.stop()
    await registry.stop_all()
    await mqtt_client.disconnect()
    await bus.shutdown()
    logger.info("all_components_stopped")


def create_app(config: ConfigLoader | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        config: Application configuration loader.
                If None, a default config is loaded.

    Returns:
        Configured FastAPI application instance.
    """
    global _app_config

    if config is None:
        config = ConfigLoader.load("config/config.yaml")
    _app_config = config

    # Store config in a temporary holder so lifespan can access it via app.state
    # We set app.state.config after creating the app below

    # Get API settings
    swagger_enabled = config.get("api", "swagger_enabled", default=True)
    cors_origins = config.get("api", "cors_origins", default=["*"])

    app = FastAPI(
        title="PresenceHub API",
        description="The best residential presence detection service for Home Assistant",
        version="0.1.0",
        docs_url="/docs" if swagger_enabled else None,
        redoc_url="/redoc" if swagger_enabled else None,
        openapi_url="/openapi.json" if swagger_enabled else None,
        lifespan=lifespan,
    )

    # Store config on app.state for lifespan access
    app.state.config = config

    # Setup middleware
    setup_middleware(app, cors_origins)

    # Register routes
    app.include_router(devices_router)
    app.include_router(history_router)
    app.include_router(stats_router)
    app.include_router(health_router)
    app.include_router(metrics_router)

    return app
