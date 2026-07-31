# PresenceHub

> The best residential presence detection service for Home Assistant.

**PresenceHub** detects all devices on your local network using multiple simultaneous detection sources, calculates a confidence score to eliminate false positives, and publishes presence data to Home Assistant via MQTT — with zero manual configuration.

![Python](https://img.shields.io/badge/python-3.13-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![Vue](https://img.shields.io/badge/Vue-3.5-4FC08D)
![License](https://img.shields.io/badge/license-MIT-brightgreen)
![Tests](https://img.shields.io/badge/tests-62%20passed-success)

---

## Architecture

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│   ARP    │   │   mDNS   │   │   Ping   │   │   DHCP   │
│ +100     │   │ +90      │   │ +40      │   │ +80      │
└────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘
     │               │               │               │
     └───────────────┴───────┬───────┴───────────────┘
                             │  DEVICE_DETECTED
                             ▼
                    ┌─────────────────┐
                    │   EventBus      │
                    │ (Async pub/sub) │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
     ┌────────────┐  ┌────────────┐  ┌────────────┐
     │ Presence   │  │   MQTT     │  │    HA      │
     │ Engine     │  │ Publisher  │  │ Discovery  │
     └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
           │               │               │
           ▼               ▼               ▼
     ┌────────────┐  ┌────────────┐  ┌────────────┐
     │ Confidence │  │ Mosquitto  │──│   Home     │
     │ Calculator │  │   Broker   │  │ Assistant  │
     └─────┬──────┘  └────────────┘  └────────────┘
           │
           ▼
     ┌────────────┐     ┌────────────┐
     │  Device    │────▶│  SQLite    │
     │  Manager   │     │  Database  │
     └────────────┘     └────────────┘
```

## Confidence Score System

Each detection source contributes points to a cumulative confidence score, capped at 100:

| Source | Points | Reliability |
|--------|--------|-------------|
| ARP | **100** | Direct kernel-level MAC-IP mapping |
| mDNS | **90** | Devices actively announce themselves |
| DHCP | **80** | DHCP server lease records |
| MQTT | **70** | MQTT-based presence reports |
| Ping | **40** | ICMP reachability (some devices block) |

**Online threshold**: score ≥ 50 → `ONLINE`, otherwise → `OFFLINE`.

Scores decay automatically by 5 points per cycle (configurable), preventing stale devices from staying online forever.

## Quick Start

### Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/presencehub/presencehub.git
cd presencehub

# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Stop all services
docker compose down
```

This starts:
- **PresenceHub Backend** on port `8000`
- **Web UI** on port `80`
- **Mosquitto MQTT Broker** on port `1883`

### Local Development

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run the server
python -m api.server

# Or run with hot reload
uvicorn api.app:create_app --factory --host 0.0.0.0 --port 8000 --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server runs on port `5173` with API proxy to `localhost:8000`.

## Home Assistant Integration

PresenceHub uses **MQTT Discovery** — no YAML configuration needed in Home Assistant.

1. Ensure your Home Assistant has the MQTT integration configured
2. Point it to the PresenceHub Mosquitto broker (`localhost:1883` or container host)
3. Devices will automatically appear as:
   - `binary_sensor.presence_<mac>` — presence sensor
   - `device_tracker.tracker_<mac>` — device tracker

Each device entity includes manufacturer, model, and suggested area.

### MQTT Topics

| Topic | Payload | Description |
|-------|---------|-------------|
| `home/presence/status` | `online`/`offline` | Service availability (LWT) |
| `home/presence/<mac>/status` | `online`/`offline` | Device presence status |
| `home/presence/<mac>/json` | JSON | Full device details |

### JSON Payload Example

```json
{
  "name": "Thyago's Phone",
  "online": true,
  "hostname": "iphone",
  "ip": "192.168.1.120",
  "mac": "AA:BB:CC:DD:EE:FF",
  "vendor": "Apple",
  "confidence": 100,
  "last_seen": "2026-07-31T00:00:00+00:00",
  "last_source": "arp",
  "device_type": "phone",
  "os_type": "ios"
}
```

## API Reference

Base URL: `http://localhost:8000`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/devices` | List all devices (supports `?status=online&search=`) |
| `GET` | `/devices/{mac}` | Get device by MAC |
| `POST` | `/devices` | Create device manually |
| `PUT` | `/devices/{mac}` | Update device |
| `DELETE` | `/devices/{mac}` | Delete device |
| `GET` | `/history` | Detection event history (`?mac=&source=`) |
| `GET` | `/stats` | Aggregate statistics |
| `GET` | `/health` | Liveness probe |
| `GET` | `/health/ready` | Readiness probe |
| `GET` | `/metrics` | Prometheus metrics |

Swagger UI: `http://localhost:8000/docs`

## Configuration

Edit `config/config.yaml` or use environment variables with the `PH_` prefix:

```yaml
mqtt:
  host: localhost
  port: 1883

network:
  interface: eth0
  subnet: 192.168.1.0/24

presence:
  timeout: 300
  decay_interval: 60
  decay_rate: 5
  online_threshold: 50

detectors:
  arp:
    enabled: true
    interval: 60
  mdns:
    enabled: true
    interval: 30
  ping:
    enabled: true
    interval: 120
  dhcp:
    enabled: true
    interval: 60
```

Environment variable overrides:
```bash
export PH_MQTT_HOST=192.168.1.10
export PH_PRESENCE_ONLINE_THRESHOLD=60
export PH_DETECTORS_ARP_ENABLED=false
```

## Project Structure

```
PresenceHub/
├── core/           # Domain interfaces, EventBus, types, exceptions
├── models/         # Domain entities (Device, DetectionResult, ConfidenceScore)
├── detectors/      # Presence detectors (ARP, mDNS, Ping, DHCP)
│   ├── arp/        # ARP table scanner (Linux/macOS/Windows)
│   ├── mdns/       # mDNS/Bonjour discovery (zeroconf)
│   ├── ping/       # ICMP ping sweep
│   └── dhcp/       # DHCP lease file parser (dnsmasq, dhcpd, udhcpd)
├── services/       # Business logic (PresenceEngine, ConfidenceCalculator)
├── mqtt/           # MQTT client, publisher, HA discovery
├── api/            # FastAPI REST API (routes, schemas, middleware)
├── database/       # SQLAlchemy models, repositories, migrations
├── workers/        # Background tasks (decay, cleanup)
├── config/         # YAML configuration loader
├── utils/          # Logging, network helpers
├── frontend/       # Vue 3 + Vite + TypeScript + TailwindCSS
├── docker/         # Dockerfiles and Mosquitto config
└── tests/          # Unit and integration tests (62+ tests)
```

## Observability

- **Health checks**: `/health` (liveness) and `/health/ready` (readiness)
- **Prometheus metrics**: `/metrics` endpoint with device counts and detection rates
- **Structured logging**: JSON-formatted logs via structlog
- **Docker healthchecks**: All containers have built-in health checks

## Roadmap

- [x] ARP, mDNS, Ping, DHCP detectors
- [x] MQTT with auto-reconnect and HA Discovery
- [x] REST API with Swagger
- [x] Vue 3 Web UI with dark mode
- [x] Docker Compose with health checks
- [x] Confidence score with decay
- [ ] ESPHome Bluetooth Proxy
- [ ] SNMP network scanning
- [ ] UniFi Controller API
- [ ] TP-Link Omada API
- [ ] MikroTik RouterOS API
- [ ] OpenWRT integration
- [ ] OPNsense/pfSense integration
- [ ] Zigbee2MQTT
- [ ] Frigate NVR
- [ ] Matter / Thread

## Development

```bash
# Run all tests
make test

# Run linters
make lint

# Run type checker
make typecheck

# Format code
make format

# Run with auto-reload
make run-dev
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License — see [LICENSE](LICENSE) for details.
