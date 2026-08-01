# Graph Report - .  (2026-07-31)

## Corpus Check
- Corpus is ~24,744 words - fits in a single context window. You may not need a graph.

## Summary
- 1003 nodes · 1841 edges · 59 communities (55 shown, 4 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 100 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Database Models (0)
- ARP & MAC Utilities (1)
- Confidence Scoring & Decay (2)
- History & Event API (3)
- Frontend API Client (4)
- API Dependencies & Middleware (5)
- Ping Detector (6)
- Configuration Management (7)
- API Dependencies & Middleware (8)
- MQTT Client & Publisher (9)
- DHCP Detector (10)
- Database Models (11)
- Configuration Management (12)
- Integration & Unit Tests (13)
- Configuration Management (14)
- Models Detection (15)
- Database Models (16)
- Detectors Init (17)
- MQTT Client & Publisher (18)
- Database Models (19)
- Detectors Base Basedetector (20)
- MQTT Client & Publisher (21)
- Api App (22)
- History & Event API (23)
- Confidence Scoring & Decay (24)
- Confidence Scoring & Decay (25)
- MQTT Client & Publisher (26)
- Detectors Mdns Detector Mdnsde (27)
- MQTT Client & Publisher (28)
- DHCP Detector (29)
- Confidence Scoring & Decay (30)
- Api Middleware (31)
- ARP & MAC Utilities (32)
- Services Device Manager (33)
- Integration & Unit Tests (34)
- History & Event API (35)
- MQTT Client & Publisher (36)
- Core Interfaces Rationale 129 (37)
- MQTT Client & Publisher (38)
- Api Routes Health (39)
- Api Routes Init (40)
- History & Event API (41)
- History & Event API (42)
- Database Models (43)
- Frontend Vue Application (44)
- Pkg Presencehub (51)

## God Nodes (most connected - your core abstractions)
1. `AsyncioEventBus` - 56 edges
2. `ConfigLoader` - 42 edges
3. `DeviceRepository` - 37 edges
4. `DetectionSource` - 35 edges
5. `MqttClient` - 35 edges
6. `ConfidenceCalculator` - 32 edges
7. `ArpDetector` - 31 edges
8. `EventType` - 30 edges
9. `Device` - 28 edges
10. `PingDetector` - 26 edges

## Surprising Connections (you probably didn't know these)
- `ConfigLoader` --uses--> `InvalidConfigurationError`  [INFERRED]
  config/loader.py → core/exceptions.py
- `ArpDetector` --uses--> `ConfigLoader`  [INFERRED]
  detectors/arp/detector.py → config/loader.py
- `BaseDetector` --uses--> `ConfigLoader`  [INFERRED]
  detectors/base.py → config/loader.py
- `DhcpDetector` --uses--> `ConfigLoader`  [INFERRED]
  detectors/dhcp/detector.py → config/loader.py
- `MdnsDetector` --uses--> `ConfigLoader`  [INFERRED]
  detectors/mdns/detector.py → config/loader.py

## Import Cycles
- None detected.

## Communities (59 total, 4 thin omitted)

### Community 0 - "Database Models (0)"
Cohesion: 0.06
Nodes (39): Base, SQLAlchemy declarative base for PresenceHub database models.  All ORM models inh, Declarative base for all SQLAlchemy ORM models., DeviceModel, Any, Device ORM model — SQLAlchemy mapping for the devices table.  Persists device st, SQLAlchemy ORM model for the 'devices' table.      Maps to the Device domain mod, Convert the ORM model to a dictionary. (+31 more)

### Community 1 - "ARP & MAC Utilities (1)"
Cohesion: 0.06
Nodes (27): normalize_mac(), MacAddress, Normalize a MAC address to uppercase colon-separated format.      Args:, ArpDetector, Any, Fallback: Read ARP table from /proc/net/arp (Linux).          Used only when 'ip, Read ARP table using 'arp -a' (macOS/BSD).          Format examples:, Detects devices by reading the system ARP table.      The ARP table contains MAC (+19 more)

### Community 2 - "Confidence Scoring & Decay (2)"
Cohesion: 0.07
Nodes (26): DeviceStatus, Device online/offline status., ConfidenceCalculator, ConfidenceValue, MacAddress, Get the online/offline status for a device.          Args:             mac: Devi, Apply decay to all tracked devices.          First expires detection sources tha, Remove a device from confidence tracking.          Args:             mac: Device (+18 more)

### Community 3 - "History & Event API (3)"
Cohesion: 0.08
Nodes (25): ABC, Configuration loader with YAML file support, env var overrides, and deep merge., Asynchronous EventBus implementation.  Provides the concrete implementation of t, EventHandlerError, Raised when an event handler throws an exception., Core layer of PresenceHub — domain primitives, interfaces, and the EventBus.  Al, EventBus, PresenceDetector (+17 more)

### Community 4 - "Frontend API Client (4)"
Cohesion: 0.07
Nodes (21): api, Device, DeviceListResponse, fetchDevices(), fetchHistory(), fetchMqttStatus(), fetchStats(), HistoryEvent (+13 more)

### Community 5 - "API Dependencies & Middleware (5)"
Cohesion: 0.09
Nodes (35): get_device_manager(), get_event_bus(), Any, Request, Dependency that provides the active DeviceManager instance., Dependency that provides the active EventBus instance., create_device(), delete_device() (+27 more)

### Community 6 - "Ping Detector (6)"
Cohesion: 0.07
Nodes (20): PingDetector, Any, Ping a single host using the system ping command.          Args:             ip:, Extract hostname from ping output if available.          Args:             outpu, Check if a single IP is reachable.          Convenience method for other compone, Detects devices by sending ICMP ping requests.      Pings known IPs from the dev, Execute a ping sweep of known IPs or subnet.          Strategy:             1. P, Get the list of IPs to ping.          Scans all usable hosts in the configured s (+12 more)

### Community 7 - "Configuration Management (7)"
Cohesion: 0.08
Nodes (27): ConfigurationError, DetectionError, DetectorStartError, DetectorStopError, DeviceAlreadyExistsError, DeviceError, DeviceNotFoundError, EventBusError (+19 more)

### Community 8 - "API Dependencies & Middleware (8)"
Cohesion: 0.06
Nodes (32): autoprefixer, axios, dependencies, axios, pinia, vue, vue-router, devDependencies (+24 more)

### Community 9 - "MQTT Client & Publisher (9)"
Cohesion: 0.10
Nodes (19): MqttClient, Subscribe to an MQTT topic.          Inbound messages are routed to the EventBus, Async MQTT client with auto-reconnect and health monitoring.      Wraps aiomqtt., Whether the client is currently connected to the broker., HADiscovery, Any, Remove discovery entries for a device (publish empty config).          Args:, Publishes Home Assistant MQTT Discovery configurations.      When a new device i (+11 more)

### Community 10 - "DHCP Detector (10)"
Cohesion: 0.09
Nodes (17): DhcpDetector, Any, Parse dnsmasq lease file format.          Format:             <lease_expiry> <ma, Parse ISC DHCPd lease file format.          Format:             lease 192.168.1., Parse udhcpd (OpenWRT) lease file format.          Format:             <mac> <ip, Detects devices by parsing DHCP lease files.      Reads lease files from common, Parse all configured DHCP lease files and publish discovered devices., Parse a DHCP lease file and extract device entries.          Auto-detects the le (+9 more)

### Community 11 - "Database Models (11)"
Cohesion: 0.10
Nodes (18): get_history(), Any, Get detection event history.      Args:         mac: Optional MAC address filter, DetectionEventModel, SQLAlchemy ORM model for the 'detection_events' table.      Records every indivi, EventRepository, Any, AsyncSession (+10 more)

### Community 12 - "Configuration Management (12)"
Cohesion: 0.10
Nodes (19): Default configuration values for PresenceHub.  These defaults are merged with us, Configuration layer for PresenceHub.  Handles loading, validation, and access to, _cast_env_value(), ConfigLoader, _deep_merge(), _env_override(), load_config(), Any (+11 more)

### Community 13 - "Integration & Unit Tests (13)"
Cohesion: 0.11
Nodes (15): AsyncClient, Verify duplicate device creation returns 409., Verify updating a device., Integration tests for the REST API., Verify deleting a device., Verify getting a nonexistent device returns 404., Verify stats endpoint returns aggregate data., Verify history endpoint. (+7 more)

### Community 14 - "Configuration Management (14)"
Cohesion: 0.07
Nodes (26): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleDetection, moduleResolution (+18 more)

### Community 15 - "Models Detection (15)"
Cohesion: 0.13
Nodes (17): DetectionResult, Detection result domain models.  Represents the output of a presence detector —, Result of a single presence detection from a detector.      Each detector publis, Serialize to a dictionary.          Returns:             Dictionary representati, Device domain model.  The Device is the central domain entity representing a det, DetectionSource, OperatingSystem, StrEnum (+9 more)

### Community 16 - "Database Models (16)"
Cohesion: 0.11
Nodes (17): async_sessionmaker, get_session_factory(), AsyncSession, Get the session factory.      Returns:         The async session factory.      R, Device, MacAddress, Get all cached devices.          Returns:             List of all cached Device, Get all online devices from cache.          Returns:             List of online (+9 more)

### Community 17 - "Detectors Init (17)"
Cohesion: 0.09
Nodes (13): Detectors layer for PresenceHub.  Each detector is a self-contained module imple, DetectorRegistry, Stop all registered detectors gracefully.          Detectors are stopped concurr, Check health of all detectors.          Returns:             Dictionary mapping, Start a detector, catching and logging errors.          Args:             name:, Stop a detector, catching and logging errors.          Args:             name: D, Register a custom detector factory.          Allows external plugins or future d, Manages detector instances and their lifecycle.      Loads enabled detectors fro (+5 more)

### Community 18 - "MQTT Client & Publisher (18)"
Cohesion: 0.17
Nodes (18): MQTT module for PresenceHub.  Provides async MQTT client with auto-reconnect, de, MQTT Device Presence Publisher.  Listens to device events on the internal EventB, device_presence_payload(), _get_device_icon(), _get_suggested_area(), ha_binary_sensor_discovery(), ha_device_tracker_discovery(), online_payload() (+10 more)

### Community 19 - "Database Models (19)"
Cohesion: 0.14
Nodes (16): get_config(), get_device_repo(), get_event_repo(), FastAPI dependency injection.  Provides reusable dependencies for database sessi, Dependency that provides a DeviceRepository with an active session.      Yields:, Dependency that provides an EventRepository with an active session.      Yields:, Dependency that provides the application ConfigLoader.      Returns:         The, close_database() (+8 more)

### Community 20 - "Detectors Base Basedetector (20)"
Cohesion: 0.11
Nodes (12): BaseDetector, Any, Check whether the detector is healthy.          Returns:             True if the, Main detection loop: runs _scan_impl at the configured interval.          Handle, Execute a single detection scan.          Subclasses implement the actual detect, Publish a batch of detection results to the EventBus.          Args:, Abstract base class for all presence detectors.      Provides:         - Standar, Initialize the base detector.          Args:             config: Application con (+4 more)

### Community 21 - "MQTT Client & Publisher (21)"
Cohesion: 0.16
Nodes (13): MqttPublisher, Any, Device, EventPayload, Handle DEVICE_ONLINE event — publish online status., Handle DEVICE_OFFLINE event — publish offline status., Handle DEVICE_UPDATED event — publish updated device., Handle DEVICE_DETECTED event — publish detected device.          This publishes (+5 more)

### Community 22 - "Api App (22)"
Cohesion: 0.15
Nodes (13): create_app(), lifespan(), Any, FastAPI, FastAPI application factory for PresenceHub.  Creates and configures the FastAPI, Create and configure the FastAPI application.      Args:         config: Applica, Application lifespan handler — startup and shutdown.      Initializes and starts, API layer for PresenceHub — FastAPI application. (+5 more)

### Community 23 - "History & Event API (23)"
Cohesion: 0.16
Nodes (16): main(), PresenceHub server entry point.  Starts the Uvicorn ASGI server with the FastAPI, Initialize and start the PresenceHub server., BoundLogger, EventDict, Utility modules for PresenceHub.  Contains logging configuration, network helper, _add_process_id(), configure_logging() (+8 more)

### Community 24 - "Confidence Scoring & Decay (24)"
Cohesion: 0.11
Nodes (11): DeviceId, Device, ConfidenceValue, Serialize the device to a JSON-compatible dictionary.          Returns:, Represents a detected network device with presence tracking.      Attributes:, The device unique identifier (its MAC address)., Convenience property for online status check., Update last_seen and optionally last_source.          Args:             source: (+3 more)

### Community 25 - "Confidence Scoring & Decay (25)"
Cohesion: 0.13
Nodes (11): ConfidenceScore, ConfidenceValue, Recalculate the confidence score as sum of source points, capped at 100., Apply decay to the confidence score.          Reduces the score by the given rat, Reset the confidence score to zero., Whether the device is considered online based on its score., Serialize to dictionary., Tracks and calculates the confidence score for a device.      The score is the s (+3 more)

### Community 26 - "MQTT Client & Publisher (26)"
Cohesion: 0.15
Nodes (10): Device, Verify fallback name when friendly_name is empty., Tests for MQTT payload schemas., Verify online payload returns 'online'., Verify offline payload returns 'offline'., Verify full JSON payload for online device., Verify full JSON payload for offline device., Verify HA binary_sensor discovery payload. (+2 more)

### Community 27 - "Detectors Mdns Detector Mdnsde (27)"
Cohesion: 0.12
Nodes (9): MdnsDetector, Any, Perform a one-shot mDNS query using system tools (dns-sd / avahi-browse)., Detects devices via mDNS/DNS-SD service discovery.      Uses zeroconf to listen, Start the mDNS listener.          Overrides BaseDetector.start() to also initial, Stop the mDNS listener and clean up zeroconf resources., Execute a single mDNS discovery scan.          Queries for common service types, Continuously listen for mDNS announcements using zeroconf.          Runs a Servi (+1 more)

### Community 28 - "MQTT Client & Publisher (28)"
Cohesion: 0.14
Nodes (9): Any, Publish a message to an MQTT topic.          Args:             topic: MQTT topic, Maintain MQTT connection with exponential backoff reconnection.          Runs in, Establish a single MQTT connection., Process incoming MQTT messages.          Routes each message to the EventBus as, Publish online availability status., Publish offline availability status., Connect to the MQTT broker and start the reconnect loop.          Publishes onli (+1 more)

### Community 29 - "DHCP Detector (29)"
Cohesion: 0.19
Nodes (9): EventType, StrEnum, Domain event type constants for the PresenceHub system.  All event types are cen, Centralized registry of all domain event types., Async MQTT Client with auto-reconnect for PresenceHub.  Provides a robust MQTT c, Home Assistant MQTT Discovery integration.  Automatically creates binary_sensor, Unit tests for the DhcpDetector., Unit tests for the MdnsDetector. (+1 more)

### Community 30 - "Confidence Scoring & Decay (30)"
Cohesion: 0.14
Nodes (9): PresenceEngine, EventPayload, Apply confidence decay to all tracked devices.          Devices whose confidence, Generate a deterministic synthetic MAC address from an IP.          Uses the loc, Central presence detection engine.      Listens for DEVICE_DETECTED events from, Initialize the PresenceEngine.          Args:             bus: Internal EventBus, Subscribe to relevant events on the EventBus., Handle a DEVICE_DETECTED event from any detector.          Processes the detecti (+1 more)

### Community 31 - "Api Middleware (31)"
Cohesion: 0.21
Nodes (11): FastAPI, Request, FastAPI middleware — CORS, request ID, timing., Adds a unique X-Request-ID header to every response., Logs request method, path, status, and duration., Configure all middleware for the FastAPI application.      Args:         app: Fa, RequestIDMiddleware, RequestTimingMiddleware (+3 more)

### Community 32 - "ARP & MAC Utilities (32)"
Cohesion: 0.15
Nodes (7): AsyncioEventBus, Gracefully shut down the event bus.          Sets the shutdown flag and waits fo, Asyncio-based EventBus implementation.      Features:         - Multiple subscri, Initialize the MQTT client.          Args:             config: Application confi, event_bus(), Shared pytest fixtures for PresenceHub tests., Provide a fresh AsyncioEventBus instance.

### Community 33 - "Services Device Manager (33)"
Cohesion: 0.24
Nodes (6): DeviceManager, Device Manager — manages device lifecycle with in-memory cache and DB persistenc, Number of devices currently in the in-memory cache., Manages device CRUD with in-memory caching and database persistence.      Device, Services layer — business logic and orchestration., Presence Engine — orchestrates detection, scoring, and device lifecycle.  The ce

### Community 34 - "Integration & Unit Tests (34)"
Cohesion: 0.18
Nodes (6): Tests for MdnsDetector lifecycle and discovery., Verify the detector name is 'mdns'., Verify detector starts and stops cleanly., Verify health check reflects running state., Verify scan publishes DEVICE_DETECTED events., TestMdnsDetector

### Community 35 - "History & Event API (35)"
Cohesion: 0.22
Nodes (6): EventHandler, EventPayload, Invoke a handler safely, logging any exceptions.          Args:             hand, Register a handler for a specific event type.          Args:             event_t, Remove a handler registration.          Args:             event_type: The event, Publish an event to all registered subscribers.          Handlers are invoked co

### Community 36 - "MQTT Client & Publisher (36)"
Cohesion: 0.29
Nodes (6): Device, EventPayload, Handle DEVICE_DETECTED event — publish discovery if new.          Args:, Handle DEVICE_UPDATED event — re-publish discovery with updated metadata., Handle MQTT_CONNECTED event — publish discovery for all known devices., Publish MQTT Discovery configs for a device.          Creates binary_sensor and

### Community 37 - "Core Interfaces Rationale 129 (37)"
Cohesion: 0.31
Nodes (3): Generic repository protocol for data access abstraction., Repository, T

### Community 38 - "MQTT Client & Publisher (38)"
Cohesion: 0.25
Nodes (7): get_mqtt_status(), get_stats(), Any, Request, Get aggregate statistics.      Returns:         Dictionary with device and event, Get MQTT broker connection status and details.      Returns:         MQTT status, The configured MQTT topic prefix.

### Community 39 - "Api Routes Health (39)"
Cohesion: 0.33
Nodes (6): health_check(), Any, Health check API routes.  Provides liveness and readiness probes for Kubernetes/, Liveness check — always returns OK if the server is running.      Returns:, Readiness check — returns OK when the app is ready to serve.      Returns:, readiness_check()

### Community 40 - "Api Routes Init (40)"
Cohesion: 0.33
Nodes (4): get_metrics(), Prometheus metrics endpoint., Prometheus metrics endpoint.      Returns:         Plain text response with Prom, Response

### Community 41 - "History & Event API (41)"
Cohesion: 0.40
Nodes (3): EventHandler, Remove a handler registration.          Args:             event_type: The event, Register a handler for a specific event type.          Args:             event_t

## Knowledge Gaps
- **51 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+46 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ConfigLoader` connect `Configuration Management (12)` to `ARP & MAC Utilities (32)`, `ARP & MAC Utilities (1)`, `History & Event API (3)`, `Ping Detector (6)`, `Configuration Management (7)`, `MQTT Client & Publisher (9)`, `DHCP Detector (10)`, `Integration & Unit Tests (13)`, `Detectors Init (17)`, `Database Models (19)`, `Detectors Base Basedetector (20)`, `Api App (22)`, `History & Event API (23)`, `Detectors Mdns Detector Mdnsde (27)`, `DHCP Detector (29)`?**
  _High betweenness centrality (0.135) - this node is a cross-community bridge._
- **Why does `AsyncioEventBus` connect `ARP & MAC Utilities (32)` to `ARP & MAC Utilities (1)`, `Services Device Manager (33)`, `History & Event API (35)`, `History & Event API (3)`, `Ping Detector (6)`, `MQTT Client & Publisher (9)`, `DHCP Detector (10)`, `Detectors Init (17)`, `MQTT Client & Publisher (18)`, `Detectors Base Basedetector (20)`, `MQTT Client & Publisher (21)`, `Api App (22)`, `Detectors Mdns Detector Mdnsde (27)`, `DHCP Detector (29)`, `Confidence Scoring & Decay (30)`?**
  _High betweenness centrality (0.127) - this node is a cross-community bridge._
- **Why does `DetectionSource` connect `Models Detection (15)` to `Database Models (0)`, `ARP & MAC Utilities (1)`, `Confidence Scoring & Decay (2)`, `History & Event API (3)`, `Services Device Manager (33)`, `Ping Detector (6)`, `DHCP Detector (10)`, `Confidence Scoring & Decay (24)`, `Confidence Scoring & Decay (25)`, `Detectors Mdns Detector Mdnsde (27)`, `Confidence Scoring & Decay (30)`?**
  _High betweenness centrality (0.110) - this node is a cross-community bridge._
- **Are the 15 inferred relationships involving `AsyncioEventBus` (e.g. with `EventType` and `EventHandlerError`) actually correct?**
  _`AsyncioEventBus` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `ConfigLoader` (e.g. with `InvalidConfigurationError` and `ArpDetector`) actually correct?**
  _`ConfigLoader` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `DeviceRepository` (e.g. with `DetectionSource` and `DeviceStatus`) actually correct?**
  _`DeviceRepository` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `DetectionSource` (e.g. with `DeviceRepository` and `ArpDetector`) actually correct?**
  _`DetectionSource` has 11 INFERRED edges - model-reasoned connections that need verification._