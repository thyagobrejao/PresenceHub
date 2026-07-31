"""Async MQTT Client with auto-reconnect for PresenceHub.

Provides a robust MQTT client built on aiomqtt with:
    - Automatic reconnection with exponential backoff
    - Connection health monitoring
    - LWT (Last Will and Testament)
    - Inbound message routing to EventBus
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import aiomqtt
import structlog

from config.loader import ConfigLoader
from core.bus import AsyncioEventBus
from core.events import EventType

logger = structlog.get_logger(__name__)


class MqttClient:
    """Async MQTT client with auto-reconnect and health monitoring.

    Wraps aiomqtt.Client with exponential backoff reconnection,
    LWT support, and event bus integration for inbound messages.

    Usage:
        client = MqttClient(config, bus)
        await client.connect()
        await client.publish("home/presence/device", "online")
        await client.disconnect()
    """

    def __init__(self, config: ConfigLoader, bus: AsyncioEventBus) -> None:
        """Initialize the MQTT client.

        Args:
            config: Application configuration.
            bus: Internal EventBus for routing inbound MQTT messages.
        """
        self._config = config
        self._bus = bus
        self._client: aiomqtt.Client | None = None
        self._connected = False
        self._running = False
        self._reconnect_task: asyncio.Task[None] | None = None

        # MQTT configuration
        self._host = config.get("mqtt", "host", default="localhost")
        self._port = config.get("mqtt", "port", default=1883)
        self._username = config.get("mqtt", "username", default="")
        self._password = config.get("mqtt", "password", default="")
        self._client_id = config.get("mqtt", "client_id", default="presencehub")
        self._keepalive = config.get("mqtt", "keepalive", default=60)
        self._topic_prefix = config.get("mqtt", "topic_prefix", default="home/presence")
        self._reconnect_interval = config.get("mqtt", "reconnect_interval", default=5)
        self._reconnect_max = config.get("mqtt", "reconnect_max_interval", default=60)

    @property
    def is_connected(self) -> bool:
        """Whether the client is currently connected to the broker."""
        return self._connected

    @property
    def topic_prefix(self) -> str:
        """The configured MQTT topic prefix."""
        return self._topic_prefix

    async def connect(self) -> None:
        """Connect to the MQTT broker and start the reconnect loop.

        Publishes online status and availability after connecting.
        """
        self._running = True
        self._reconnect_task = asyncio.create_task(self._reconnect_loop(), name="mqtt-reconnect")
        logger.info("mqtt_connecting", host=self._host, port=self._port)

    async def disconnect(self) -> None:
        """Disconnect from the MQTT broker gracefully.

        Publishes offline LWT before disconnecting.
        """
        self._running = False

        # Publish offline status before disconnecting
        try:
            await self._publish_offline()
        except Exception:
            pass

        if self._client:
            try:
                await self._client.__aexit__(None, None, None)
            except Exception:
                pass
            self._client = None

        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass

        self._connected = False
        logger.info("mqtt_disconnected")

    async def publish(
        self,
        topic: str,
        payload: str | dict[str, Any],
        qos: int = 1,
        retain: bool = False,
    ) -> None:
        """Publish a message to an MQTT topic.

        Args:
            topic: MQTT topic (will be prefixed with topic_prefix).
            payload: String or dict payload (dicts are JSON-encoded).
            qos: MQTT QoS level (0, 1, or 2).
            retain: Whether to retain the message.

        Raises:
            RuntimeError: If the client is not connected.
        """
        if not self._client or not self._connected:
            raise RuntimeError("MQTT client not connected")

        if isinstance(payload, dict):
            payload = json.dumps(payload)

        await self._client.publish(topic, payload, qos=qos, retain=retain)

    async def subscribe(self, topic: str, qos: int = 1) -> None:
        """Subscribe to an MQTT topic.

        Inbound messages are routed to the EventBus as MQTT_MESSAGE events.

        Args:
            topic: MQTT topic to subscribe to.
            qos: MQTT QoS level.
        """
        if not self._client:
            raise RuntimeError("MQTT client not connected")
        await self._client.subscribe(topic, qos=qos)
        logger.debug("mqtt_subscribed", topic=topic)

    async def _reconnect_loop(self) -> None:
        """Maintain MQTT connection with exponential backoff reconnection.

        Runs indefinitely while self._running is True.
        """
        backoff = self._reconnect_interval

        while self._running:
            try:
                await self._connect_once()
                backoff = self._reconnect_interval  # Reset on success

                # Connection established — process messages
                await self._message_loop()

            except asyncio.CancelledError:
                break
            except Exception as exc:
                self._connected = False
                logger.warning(
                    "mqtt_connection_failed",
                    host=self._host,
                    port=self._port,
                    error=str(exc) or repr(exc),
                    reconnect_in=backoff,
                )
                try:
                    await self._bus.publish(EventType.MQTT_DISCONNECTED, {"reason": str(exc)})
                except Exception:
                    pass

                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self._reconnect_max)

    async def _connect_once(self) -> None:
        """Establish a single MQTT connection."""
        auth: dict[str, str] | None = None
        if self._username:
            auth = {"username": self._username, "password": self._password}

        will = aiomqtt.Will(
            topic=f"{self._topic_prefix}/status",
            payload="offline",
            qos=1,
            retain=True,
        )

        self._client = aiomqtt.Client(
            hostname=self._host,
            port=self._port,
            client_id=self._client_id,
            username=self._username or None,
            password=self._password or None,
            keepalive=self._keepalive,
            will=will,
        )

        await self._client.__aenter__()
        self._connected = True
        logger.info("mqtt_connected", host=self._host, port=self._port)

        # Publish online status
        await self._publish_online()
        await self._bus.publish(EventType.MQTT_CONNECTED, {"host": self._host, "port": self._port})

    async def _message_loop(self) -> None:
        """Process incoming MQTT messages.

        Routes each message to the EventBus as an MQTT_MESSAGE event.
        """
        if not self._client:
            return

        async for message in self._client.messages:
            payload_str = message.payload.decode("utf-8") if isinstance(message.payload, bytes) else str(message.payload)

            # Try to parse JSON payload
            parsed: Any = payload_str
            try:
                parsed = json.loads(payload_str)
            except (json.JSONDecodeError, TypeError):
                pass

            await self._bus.publish(
                EventType.MQTT_MESSAGE,
                {
                    "topic": message.topic.value,
                    "payload": parsed,
                    "qos": message.qos.value,
                    "retain": message.retain,
                },
            )

    async def _publish_online(self) -> None:
        """Publish online availability status."""
        if self._client and self._connected:
            await self._client.publish(
                f"{self._topic_prefix}/status",
                "online",
                qos=1,
                retain=True,
            )

    async def _publish_offline(self) -> None:
        """Publish offline availability status."""
        if self._client and self._connected:
            await self._client.publish(
                f"{self._topic_prefix}/status",
                "offline",
                qos=1,
                retain=True,
            )
