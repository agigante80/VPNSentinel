# VPN Sentinel

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue)](https://docs.docker.com/compose/)
[![Python](https://img.shields.io/badge/Python-3.11+-green)](https://python.org)

**Real-time VPN monitoring with DNS leak detection, traffic light status indicators, and instant Telegram notifications. Know immediately when your VPN fails.**

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Dashboard](#dashboard)
- [Telegram Integration](#telegram-integration)
- [Configuration](#configuration)
- [Deployment Scenarios](#deployment-scenarios)
- [Development](#development)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

VPN Sentinel is a **distributed monitoring system** designed to continuously verify VPN connections are working correctly. It detects silent VPN failures, DNS leaks, and IP address exposure before they become security incidents.

### The Problem

- **Silent VPN Failures**: VPN connections can drop without warning, exposing your real IP address
- **DNS Leaks**: DNS queries bypass VPN protection, revealing your location to ISPs and websites
- **No Built-in Monitoring**: Most VPN clients lack health monitoring or alerting capabilities
- **Delayed Detection**: You only discover VPN issues after sensitive data has been exposed

### The Solution

VPN Sentinel provides **continuous, automated verification** with:

- **Traffic Light Status System**: Instant visual status for each client (Green/Yellow/Red)
- **VPN Bypass Detection**: Critical alerts when client IP matches server IP
- **DNS Leak Detection**: Automatic detection of DNS queries bypassing VPN tunnel
- **Real-time Notifications**: Instant Telegram alerts for connection issues
- **Web Dashboard**: Modern responsive interface for monitoring all clients
- **Multi-client Support**: Monitor unlimited VPN clients from a single server

---

## Key Features

### Security Monitoring

- **VPN Bypass Detection**: Critical red alerts when VPN is not routing traffic
- **DNS Leak Testing**: Detects when DNS queries expose your location
- **IP Geolocation Verification**: Ensures traffic exits from expected VPN server locations
- **Provider Validation**: Confirms your traffic routes through VPN provider networks

### Real-time Alerting

- **Telegram Bot Integration**: Instant notifications for all connection events
- **Priority-Based Alerts**: Critical (red), warning (yellow), and info (green) message types
- **Rich Notifications**: Detailed status with IP, location, provider, and DNS information
- **Connection History**: Tracks IP changes and connection events

### Modern Dashboard

![VPN Sentinel Dashboard](docs/images/dashboard-screenshot.png)

- **Traffic Light Status Indicators**: Green (secure), Yellow (DNS issues), Red (VPN bypass)
- **Server Information**: View server's public IP, location, and DNS status
- **Client Table**: Comprehensive table with all connected clients
- **Auto-refresh**: Updates every 30 seconds
- **Responsive Design**: Works on mobile, tablet, and desktop
- **Last Seen Timestamps**: "Just now", "5 min ago", "2h ago" format

### Flexible Architecture

- **Network Isolation**: Client runs inside VPN network, server on host network
- **VPN Provider Agnostic**: Works with OpenVPN, WireGuard, or any VPN solution
- **Docker Native**: Containerized deployment with Docker Compose
- **Multi-process Design**: Optional dedicated health monitoring service
- **Scalable**: Single server monitors multiple distributed clients

---

## Architecture

VPN Sentinel uses a **client-server architecture** with network isolation to ensure accurate monitoring.

### Network Flow Diagram

```
                                           
┌────────────────────────────────────────────────────────────┐
│                     VPN Container                          │
│  ┌────────────────┐           ┌──────────────────────────┐ │
│  │  VPN Client    │           │  VPN Sentinel Client     │ │
│  │  (OpenVPN/WG)  │◄─────────►│  - Monitors connection   │ │
│  │                │           │  - Checks public IP      │ │
│  │  tun0/wg0      │           │  - DNS leak testing      │ │
│  └────────────────┘           │  - Sends keepalives      │ │
│                                └─────────────────────────┘ │
└──────────────────────────────────────┬─────────────────────┘
                                       |
                                       | HTTP/HTTPS
                                       | (via VPN tunnel)
                                       |
                                       v
                            ┌──────────────────────┐
                            │   INTERNET/CLOUD     │
                            │                      │
                            │  Public APIs:        │
                            │  - ipinfo.io         │
                            │  - DNS leak tests    │
                            └──────────┬───────────┘
                                       |
                                       | Reaches server
                                       | via public internet
                                       v
┌──────────────────────────────────────────────────────────┐
│                     Host Network                         │
│  ┌────────────────────────────────────────────────────┐  │
│  │           VPN Sentinel Server                      │  │
│  │                                                    │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────┐ │  │
│  │  │   API       │  │  Dashboard   │  │  Telegram  │ │  │
│  │  │ Port 5000   │  │  Port 8080   │  │    Bot     │ │  │
│  │  │             │  │              │  │            │ │  │
│  │  │ - Keepalive │  │ - Web UI     │  │ - Alerts   │ │  │
│  │  │ - Status    │  │ - Traffic    │  │ - Status   │ │  │
│  │  │ - Health    │  │   lights     │  │ - History  │ │  │
│  │  └─────────────┘  └──────────────┘  └────────────┘ │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
           ^                    ^                    ^
           |                    |                    |
      API Access          Web Browser         Telegram App
```

### How It Works

1. **VPN Sentinel Client** runs inside the VPN container's network namespace
2. **All client traffic** (including monitoring) flows through the VPN tunnel
3. **Client reaches internet** via VPN, checks its public IP and DNS
4. **Client sends keepalive** to server with connection status (via internet, not Docker network)
5. **Server receives data** on host network, validates VPN is working correctly
6. **Server compares IPs**: If client IP == server IP, VPN is bypassed (RED alert)
7. **Server sends notifications** via Telegram for any issues
8. **Dashboard displays** real-time status with traffic light indicators

### Traffic Light Status System

| Status | Color | Condition | Meaning |
|--------|-------|-----------|---------|
| **Secure** | 🟢 Green | Client IP != Server IP<br>DNS location matches VPN | VPN working correctly |
| **DNS Leak** | 🟡 Yellow | DNS location != VPN country | DNS queries bypassing VPN |
| **DNS Unknown** | 🟡 Yellow | Cannot determine DNS location | DNS status unverifiable |
| **VPN Bypass** | 🔴 Red | Client IP == Server IP | **CRITICAL**: VPN not routing traffic! |

### Component Details

#### VPN Sentinel Client
- **Deployment**: Inside VPN container using `network_mode: service:vpn-container`
- **Language**: Bash + Python
- **Functions**:
  - Periodic health checks (configurable interval)
  - Public IP detection via ipinfo.io
  - DNS leak testing
  - Geolocation verification
  - Keepalive transmission to server

#### VPN Sentinel Server
- **Deployment**: Host network (requires internet access)
- **Language**: Python 3.11+ with Flask
- **Services**:
  - **API Server** (port 5000): Receives client keepalives
  - **Health Server** (port 8081): Health check endpoint
  - **Dashboard** (port 8080): Web interface
  - **Telegram Bot**: Notification delivery
- **Features**:
  - Multi-client status tracking
  - Server IP caching (reduces API calls)
  - Rate limiting and security middleware
  - Auto-cleanup of stale clients

---

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/agigante80/VPNSentinel.git
cd VPNSentinel
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

**Minimum Required Configuration:**

```env
# API Key for client-server authentication
VPN_SENTINEL_API_KEY=your-secure-api-key-here

# Telegram (optional but recommended)
VPN_SENTINEL_TELEGRAM_BOT_TOKEN=your-telegram-bot-token
VPN_SENTINEL_TELEGRAM_CHAT_ID=your-chat-id
```

### 3. Start with Docker Compose

```bash
# All-in-one deployment (server + client + VPN)
docker compose up -d

# Or server only (if clients are remote)
docker compose up -d vpn-sentinel-server
```

### 4. Verify Deployment

```bash
# Check server health
curl http://localhost:18081/health

# View dashboard
open http://localhost:18080/dashboard

# Check logs
docker logs vpn-sentinel-server
docker logs vpn-sentinel-client
```

---

## Dashboard

Access the web dashboard at: **http://server-ip:8080/dashboard**

### Features

- **Server Status Box**: Shows server's public IP, location, provider, and DNS status
- **Statistics Cards**: Total clients, online count, offline count
- **Client Table**: Detailed information for each monitored client
  - Client ID
  - VPN IP address
  - Location (City, Region, Country)
  - Provider/ISP
  - Last seen time
  - VPN status (traffic light)
  - DNS leak status

### Status Indicators

| Indicator | Meaning |
|-----------|---------|
| 🟢 **VPN Working** | Connection secure, DNS not leaking |
| 🟡 **DNS Leak Detected** | VPN working but DNS queries leaking |
| 🟡 **DNS Undetectable** | Cannot verify DNS status |
| 🔴 **VPN Bypass Detected!** | **CRITICAL** - VPN not routing traffic |

### Configuration

```env
# Dashboard port (default: 8080)
VPN_SENTINEL_SERVER_DASHBOARD_PORT=8080

# Enable/disable dashboard
VPN_SENTINEL_SERVER_WEB_DASHBOARD_ENABLED=true

# Auto-refresh interval (seconds)
# Note: Currently hardcoded to 30 seconds in HTML
```

### Reverse Proxy Example (Nginx)

```nginx
server {
    listen 80;
    server_name vpn-monitor.example.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

---

## Telegram Integration

Receive instant notifications for all VPN events.

### Setup Instructions

1. **Create a Bot**
   ```bash
   # Message @BotFather on Telegram
   /newbot
   # Follow instructions, save the token
   ```

2. **Get Your Chat ID**
   ```bash
   # Message your bot, then visit:
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   # Find "chat":{"id": YOUR_CHAT_ID}
   ```

3. **Configure VPN Sentinel**
   ```env
   VPN_SENTINEL_TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
   VPN_SENTINEL_TELEGRAM_CHAT_ID=123456789
   VPN_SENTINEL_TELEGRAM_ENABLED=true
   ```

### Notification Types

#### Connected Notification
```
✅ VPN Connected!

Client: home-office-vpn
VPN IP: 91.203.5.146
Location: London, ENG, GB
Provider: M247 Ltd
DNS: No leaks detected
Status: 🟢 VPN Working
```

#### DNS Leak Warning
```
⚠️ DNS Leak Detected!

Client: media-server-vpn
VPN IP: 185.200.118.50
Location: Amsterdam, NH, NL
DNS Location: US
Status: 🟡 DNS Leak Detected
```

#### VPN Bypass Alert (Critical)
```
🚨 VPN BYPASS DETECTED!

Client: home-office-vpn
Client IP: 79.116.8.43
Server IP: 79.116.8.43
Location: Madrid, MD, ES

⚠️ WARNING: VPN is NOT routing traffic!
This is a critical security issue.
```

### Bot Commands

- `/status` - Show current status of all clients
- `/help` - Display available commands

---

## Configuration

### Environment Variables

#### Server Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `VPN_SENTINEL_API_KEY` | *(required)* | API key for client authentication |
| `VPN_SENTINEL_API_PATH` | `/api/v1` | API path prefix (must match client configuration) |
| `VPN_SENTINEL_SERVER_API_PORT` | `5000` | API server port |
| `VPN_SENTINEL_SERVER_HEALTH_PORT` | `8081` | Health check port |
| `VPN_SENTINEL_SERVER_DASHBOARD_PORT` | `8080` | Web dashboard port |
| `VPN_SENTINEL_SERVER_WEB_DASHBOARD_ENABLED` | `true` | Enable/disable web dashboard (set to `false` to reduce resources) |
| `VPN_SENTINEL_TELEGRAM_ENABLED` | *(auto)* | Telegram notifications: `true` (require credentials), `false` (disable), unset (auto-enable if credentials present) |
| `TELEGRAM_BOT_TOKEN` | - | Telegram bot token (required if TELEGRAM_ENABLED=true) |
| `TELEGRAM_CHAT_ID` | - | Telegram chat ID (required if TELEGRAM_ENABLED=true) |
| `VPN_SENTINEL_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARN, ERROR) |

#### Client Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `VPN_SENTINEL_CLIENT_ID` | *(auto-generated)* | Unique client identifier (format: `vpn-monitor-{12-random-digits}`) |
| `VPN_SENTINEL_SERVER_URL` | `http://server:5000` | Server API URL |
| `VPN_SENTINEL_API_KEY` | *(required)* | API key (must match server) |
| `VPN_SENTINEL_API_PATH` | `/api/v1` | API path prefix (must match server configuration) |
| `VPN_SENTINEL_CHECK_INTERVAL` | `60` | Health check interval (seconds) |
| `VPN_SENTINEL_CLIENT_HEALTH_MONITOR_ENABLED` | `false` | Enable dedicated health monitor |
| `VPN_SENTINEL_CLIENT_HEALTH_MONITOR_PORT` | `8082` | Health monitor port |

### Configuration Notes

#### Telegram Notification Behavior

The `VPN_SENTINEL_TELEGRAM_ENABLED` variable supports **3 states**:

1. **`true`** (Explicit Enable)
   - **Requires** both `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` to be set
   - Server exits with error if credentials are missing
   - Use when you want to ensure Telegram is always active

2. **`false`** (Explicit Disable)
   - Disables Telegram even if credentials are present
   - Use in testing or when temporarily disabling notifications

3. **Unset or any other value** (Auto-Detect)
   - Automatically enables if both credentials are present
   - Silently disables if credentials are missing
   - **Recommended for most deployments**

Example configurations:
```bash
# Auto-detect (recommended)
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
# VPN_SENTINEL_TELEGRAM_ENABLED not set - will auto-enable

# Explicit enable (validates credentials)
VPN_SENTINEL_TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id

# Explicit disable
VPN_SENTINEL_TELEGRAM_ENABLED=false
```

#### Client ID Format

When `VPN_SENTINEL_CLIENT_ID` is not set, the system auto-generates a unique identifier in the format `vpn-monitor-{12-random-digits}` (e.g., `vpn-monitor-847261950382`). For production deployments, it's recommended to set meaningful client IDs like `office-vpn-primary` or `home-synology-vpn`.

### Security Best Practices

1. **Use Strong API Keys**
   ```bash
   # Generate secure random key
   openssl rand -hex 32
   ```

2. **Restrict Network Access**
   - Firewall rules to limit server access
   - Use HTTPS for production deployments
   - Consider VPN or private network for server

3. **Rotate Credentials**
   - Periodically change API keys
   - Update Telegram bot tokens if compromised

4. **Monitor Logs**
   ```bash
   docker logs -f vpn-sentinel-server | grep -E "(WARN|ERROR)"
   ```

---

## Deployment Scenarios

### Scenario 1: All-in-One (Server + Client + VPN)

**Use Case**: Single-host deployment with local VPN client

```bash
cd deployments/all-in-one
cp .env.example .env
# Edit .env
docker compose up -d
```

**Components**:
- VPN Sentinel Server (host network)
- VPN Sentinel Client (VPN network)
- VPN Client container (your VPN provider)

### Scenario 2: Distributed (Central Server + Remote Clients)

**Use Case**: Monitor multiple remote VPN clients from central server

**Server Deployment**:
```bash
cd deployments/server-central
cp .env.example .env
# Edit .env with public-facing URL
docker compose up -d
```

**Client Deployment** (on each remote host):
```bash
cd deployments/client-with-vpn
cp .env.example .env
# Edit .env with server URL
docker compose up -d
```

### Scenario 3: Existing VPN Integration

**Use Case**: Add monitoring to existing VPN setup

```yaml
services:
  my-existing-vpn:
    image: my-vpn-provider:latest
    # ... existing configuration

  vpn-sentinel-client:
    image: agigante80/vpn-sentinel-client:latest
    network_mode: service:my-existing-vpn  # Share VPN network
    environment:
      VPN_SENTINEL_SERVER_URL: http://monitoring-server:5000
      VPN_SENTINEL_API_KEY: ${VPN_SENTINEL_API_KEY}
      VPN_SENTINEL_CLIENT_ID: my-vpn-client
```

---

## Development

### Build from Source

```bash
# Build server image
docker build -t vpn-sentinel-server:latest -f vpn-sentinel-server/Dockerfile .

# Build client image
docker build -t vpn-sentinel-client:latest -f vpn-sentinel-client/Dockerfile .
```

### Local Development Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r vpn-sentinel-server/requirements.txt
pip install -r tests/requirements.txt

# Install pre-commit hooks
pip install pre-commit
pre-commit install
```

### Run Tests

```bash
# Run all tests
./tests/run_tests.sh --all

# Run specific test categories
./tests/run_tests.sh --unit
./tests/run_tests.sh --integration

# Run with coverage
./tests/run_tests.sh --coverage
```

### Code Quality

```bash
# Run linters
pre-commit run --all-files

# Type checking
mypy vpn-sentinel-server/ vpn_sentinel_common/

# Security scanning
bandit -r vpn-sentinel-server/ vpn_sentinel_common/
```

---

## Testing

### Test Structure

```
tests/
├── unit/                    # Unit tests with mocks
│   ├── test_api_routes.py
│   ├── test_telegram.py
│   └── ...
├── integration/             # Integration tests
│   ├── test_dashboard.py
│   ├── test_client_keepalive.py
│   └── ...
└── fixtures/                # Test data and helpers
    ├── sample_data.py
    └── dummy_server.py
```

### Running Tests

```bash
# Quick test run
pytest tests/unit

# Full integration tests (requires Docker)
pytest tests/integration

# With coverage report
pytest --cov=vpn_sentinel_common --cov-report=html

# View coverage
open htmlcov/index.html
```

### Test Coverage

Current coverage: **125 unit tests**, **116 integration tests**

Key areas:
- API routes and keepalive logic
- Dashboard rendering and status determination
- Telegram notification formatting
- Client health monitoring
- Security middleware and rate limiting

---

## Troubleshooting

### Client Not Connecting

**Symptoms**: No keepalives received, client offline in dashboard

**Solutions**:
1. Check client logs:
   ```bash
   docker logs vpn-sentinel-client
   ```

2. Verify API key matches:
   ```bash
   # On client
   echo $VPN_SENTINEL_API_KEY
   # On server
   docker exec vpn-sentinel-server env | grep API_KEY
   ```

3. Test network connectivity:
   ```bash
   docker exec vpn-sentinel-client curl -I http://server:5000/health
   ```

4. Check server is reachable:
   ```bash
   curl http://server-ip:5000/health
   ```

### VPN Bypass Warnings (False Positives)

**Symptoms**: Red status even though VPN is working

**Causes**:
- Server and client both behind same NAT/firewall
- Server running on same network as VPN exit point
- Testing locally with server on same machine

**Solutions**:
- Deploy server on separate network/host
- Use public server with different IP
- Adjust monitoring logic if false positives persist

### Dashboard Not Loading

**Symptoms**: 404 or blank page

**Solutions**:
1. Verify dashboard is enabled:
   ```bash
   docker exec vpn-sentinel-server env | grep DASHBOARD_ENABLED
   ```

2. Check port mapping:
   ```bash
   docker ps | grep sentinel-server
   # Should show: 0.0.0.0:8080->8080/tcp
   ```

3. Check server logs:
   ```bash
   docker logs vpn-sentinel-server | grep dashboard
   ```

### Telegram Notifications Not Working

**Symptoms**: No messages received

**Solutions**:
1. Verify bot token and chat ID:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/getMe"
   ```

2. Test bot manually:
   ```bash
   curl -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
     -d "chat_id=<CHAT_ID>&text=Test"
   ```

3. Check server logs:
   ```bash
   docker logs vpn-sentinel-server | grep -i telegram
   ```

4. Ensure `VPN_SENTINEL_TELEGRAM_ENABLED=true`

---

## Contributing

Contributions are welcome! Please follow these guidelines:

### Development Workflow

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/my-feature`
3. **Make** your changes
4. **Test** thoroughly: `./tests/run_tests.sh --all`
5. **Commit** with clear messages
6. **Push** to your fork
7. **Submit** a pull request

### Coding Standards

- Follow PEP 8 for Python code
- Use type hints where possible
- Add docstrings to functions
- Write tests for new features
- Update documentation

### Commit Message Format

```
type(scope): brief description

Detailed explanation of changes...

- Bullet points for key changes
- Reference issues: Fixes #123
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Pull Request Guidelines

- Describe the problem your PR solves
- Include screenshots for UI changes
- List breaking changes clearly
- Ensure CI passes
- Update CHANGELOG.md

---

## License

This project is licensed under the **MIT License**.

**Copyright (c) 2024 VPN Sentinel Contributors**

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

**Full License**: [MIT License](https://opensource.org/licenses/MIT)

---

## Acknowledgments

- **Flask** - Web framework
- **Docker** - Containerization platform
- **ipinfo.io** - IP geolocation API
- **Telegram** - Notification platform

---

## Support

- **Issues**: [GitHub Issues](https://github.com/agigante80/VPNSentinel/issues)
- **Discussions**: [GitHub Discussions](https://github.com/agigante80/VPNSentinel/discussions)
- **Documentation**: [docs/](docs/)

---

**Made with ❤️ for privacy and security**
