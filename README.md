# VPN Sentinel

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue)](https://docs.docker.com/compose/)
[![Python](https://img.shields.io/badge/Python-3.11+-green)](https://python.org)

**Monitor your VPN connections with real-time health checks, DNS leak detection, and instant Telegram notifications. Ensure your VPN is working correctly and get alerted immediately when issues occur.**

## 🎯 Use Case: VPN Monitoring & Security

VPN Sentinel addresses critical VPN monitoring challenges:

### **The Problem**
- **VPN Connection Failures**: VPNs can disconnect silently, leaving you exposed
- **DNS Leaks**: DNS queries can bypass VPN protection, revealing your location
- **IP Address Leaks**: Failed VPN reconnections may expose your real IP
- **No Visibility**: Traditional VPN clients provide no monitoring or alerting
- **Delayed Detection**: Issues are only discovered when it's too late

### **The Solution**
VPN Sentinel provides **continuous, automated monitoring** of your VPN connections with:
- **Real-time Health Checks**: Continuous verification that your VPN is working
- **DNS Leak Detection**: Automatic detection of DNS queries bypassing VPN
- **IP Geolocation Verification**: Ensures your traffic exits from VPN servers
- **Instant Notifications**: Telegram alerts when issues are detected
- **Historical Tracking**: Monitor connection stability over time

## 🏗️ Architecture: Independent Client-Server Design

VPN Sentinel uses a **distributed architecture** that separates monitoring concerns for maximum reliability and flexibility.

### **Network Isolation Model**

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   VPN Client    │◄────┤ VPN Sentinel    │     │ VPN Sentinel    │
│   Container     │     │    Client       │────►│    Server       │
│                 │     │ (VPN Network)   │     │ (Host Network)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              ▲                        ▲
                              │                        │
                       ┌──────┴──────┐        ┌────────┴────────┐
                       │   VPN       │        │     Internet    │
                       │   Tunnel    │        │   (Port 5000)   │
                       └─────────────┘        └─────────────────┘
```

### **Component Roles**

#### **VPN Sentinel Client**
- **Location**: Runs inside your VPN container's network namespace
- **Architecture**: Multi-process design with optional dedicated health monitoring
- **Purpose**: Monitors VPN connection health from within the protected network
- **Capabilities**:
  - **Main Process**: Checks public IP address, geolocation, and DNS leak detection
  - **Health Monitor** (optional): Dedicated health status server on port 8082
  - Sends heartbeat signals to the server with comprehensive connection data
  - Performs local health checks and system monitoring
  - Supports both single-process and multi-process operation modes

**Multi-Process Architecture:**
```
VPN Container
├── vpn-sentinel-client.sh (Main monitoring process)
├── health-monitor.py (Optional dedicated health server)
└── healthcheck.py (Container health checks)
```

#### **VPN Sentinel Server**
- **Location**: Runs on your host network (outside VPN)
- **Purpose**: Receives monitoring data and handles notifications
- **Capabilities**:
  - REST API for client communications
  - Telegram bot integration for notifications
  - Web dashboard for monitoring (future)
  - Stores connection history and analytics

### **Key Architectural Benefits**

- **Network Isolation**: Client and server operate in separate network spaces
- **VPN Independence**: Works with any VPN provider (OpenVPN, WireGuard, etc.)
- **Reliable Communication**: Uses internet-based communication, not Docker networks
- **Scalability**: Single server can monitor multiple VPN clients
- **Security**: Sensitive monitoring logic runs within VPN-protected space

## 🚀 Installation & Configuration

### **Prerequisites**
- Docker Engine 20.10+
- Docker Compose v2.0+
- Internet connectivity for API calls

### Note for contributors

The project's Dockerfiles assume the build context is the repository root so COPY instructions can reference files using repository-relative paths (for example `COPY vpn-sentinel-server/vpn-sentinel-server.py /app/`). The GitHub Actions workflow has been updated to use the repository root as the build context when building component images. When building locally, run from the repo root with a command like:

```bash
# from repository root
docker build -f vpn-sentinel-server/Dockerfile .
```

### **Quick Start (5 minutes)**

```bash
# 1. Clone repository
git clone https://github.com/agigante80/VPNSentinel.git
cd VPNSentinel

# 2. Choose deployment type
cd deployments/unified/  # Recommended for most users

# 3. Configure environment
cp .env.example .env
# Edit .env with your settings (see configuration section below)

# 4. Deploy
docker compose up -d

# 5. Check status
docker compose logs -f vpn-sentinel-client
```

### **Deployment Options**

VPN Sentinel offers flexible deployment configurations:

| Deployment | Use Case | Components |
|------------|----------|------------|
| **`unified/`** | Complete VPN + monitoring stack | VPN client + Sentinel client + Sentinel server |
| **`client-only/`** | Add monitoring to existing VPN | Sentinel client only (connects to external server) |
| **`server-only/`** | Central monitoring server | Sentinel server only (accepts multiple clients) |

### **Client Installation**

The VPN Sentinel client runs alongside your VPN container and monitors its health.

#### **Docker Compose Configuration**

```yaml
services:
  vpn-sentinel-client:
    image: agigante80/vpn-sentinel-client:latest
    network_mode: service:vpn-client  # Shares VPN network
    environment:
      # Required: Server connection
      - VPN_SENTINEL_URL=http://your-server:5000
      - VPN_SENTINEL_API_KEY=your-api-key-here

      # Optional: Client identification
      - VPN_SENTINEL_CLIENT_ID=my-vpn-monitor

      # Optional: Health check intervals
      - HEALTH_CHECK_INTERVAL=300  # seconds
      - DNS_LEAK_TOLERANCE=RO     # expected country code
    restart: unless-stopped
```

#### **Client Configuration Options**

| Environment Variable | Required | Default | Description |
|---------------------|----------|---------|-------------|
| `VPN_SENTINEL_URL` | ✅ | - | Server endpoint URL (e.g., `http://server:5000`) |
| `VPN_SENTINEL_API_KEY` | ✅ | - | Authentication key (64-char hex) |
| `VPN_SENTINEL_CLIENT_ID` | ❌ | `vpn-sentinel-client` | Unique client identifier |
| `HEALTH_CHECK_INTERVAL` | ❌ | `300` | Health check frequency (seconds) |
| `DNS_LEAK_TOLERANCE` | ❌ | - | Expected DNS country code (e.g., `US`, `RO`) |
| `CONNECT_TIMEOUT` | ❌ | `10` | API connection timeout (seconds) |
| `REQUEST_TIMEOUT` | ❌ | `30` | API request timeout (seconds) |

### **Server Installation**

The VPN Sentinel server receives monitoring data and sends notifications.

#### **Docker Compose Configuration**

```yaml
services:
  vpn-sentinel-server:
    image: agigante80/vpn-sentinel-server:latest
    ports:
      - "5000:5000"  # API port
    environment:
      # Required: Authentication
      - VPN_SENTINEL_API_KEY=your-api-key-here

      # Optional: Telegram notifications
      - TELEGRAM_BOT_TOKEN=your-bot-token
      - TELEGRAM_CHAT_ID=your-chat-id

      # Optional: Security
      - VPN_SENTINEL_SERVER_ALLOWED_IPS=192.168.1.0/24

      # Optional: Advanced settings
      - FLASK_ENV=production
      - API_RATE_LIMIT=30/minute
    volumes:
      - ./certs:/certs:ro  # For HTTPS (optional)
    restart: unless-stopped
```

#### **Client Configuration Options**

| Environment Variable | Required | Default | Description |
|---------------------|----------|---------|-------------|
| `VPN_SENTINEL_URL` | ✅ | - | Server base URL (e.g., `http://server:5000`) |
| `VPN_SENTINEL_CLIENT_ID` | ❌ | auto-generated | Unique client identifier (e.g., `office-vpn`) |
| `VPN_SENTINEL_API_KEY` | ✅ | - | Authentication key (must match server) |
| `VPN_SENTINEL_API_PATH` | ❌ | `/api/v1` | API path prefix |
| `VPN_SENTINEL_INTERVAL` | ❌ | `300` | Keepalive interval in seconds (5 minutes) |
| `VPN_SENTINEL_TIMEOUT` | ❌ | `30` | HTTP request timeout in seconds |
| `VPN_SENTINEL_GEOLOCATION_SERVICE` | ❌ | `auto` | Geolocation provider (`auto`, `ipinfo.io`, `ip-api.com`, `ipwhois.app`) |
| `VPN_SENTINEL_HEALTH_MONITOR` | ❌ | `true` | Enable dedicated health monitor process |
| `VPN_SENTINEL_ALLOW_INSECURE` | ❌ | `false` | Allow insecure HTTPS connections (not recommended) |
| `VPN_SENTINEL_TLS_CERT_PATH` | ❌ | - | Path to custom TLS certificate for HTTPS |
| `VPN_SENTINEL_DEBUG` | ❌ | `false` | Enable debug logging |
| `IPINFO_API_TOKEN` | ❌ | - | Optional ipinfo.io API token for higher rate limits |
| `TZ` | ❌ | `UTC` | System timezone for log timestamps |

#### **Server Configuration Options**

| Environment Variable | Required | Default | Description |
|---------------------|----------|---------|-------------|
| `VPN_SENTINEL_API_KEY` | ✅ | - | Authentication key (must match clients) |
| `VPN_SENTINEL_SERVER_API_PORT` | ❌ | `5000` | API server port |
| `VPN_SENTINEL_SERVER_HEALTH_PORT` | ❌ | `8081` | Health check server port |
| `VPN_SENTINEL_SERVER_DASHBOARD_PORT` | ❌ | `8080` | Web dashboard server port |
| `VPN_SENTINEL_API_PATH` | ❌ | `/api/v1` | API path prefix |
| `VPN_SENTINEL_SERVER_RATE_LIMIT` | ❌ | `30` | API rate limit (requests per minute) |
| `VPN_SENTINEL_SERVER_CHECK_INTERVAL` | ❌ | `60` | Client check interval in seconds |
| `VPN_SENTINEL_SERVER_OFFLINE_THRESHOLD` | ❌ | `300` | Mark client offline after N seconds |
| `VPN_SENTINEL_WEB_DASHBOARD_ENABLED` | ❌ | `true` | Enable web dashboard |
| `VPN_SENTINEL_SERVER_ALLOWED_IPS` | ❌ | - | IP whitelist (comma-separated, CIDR notation) |
| `VPN_SENTINEL_SERVER_IP_WHITELIST_ENABLED` | ❌ | `false` | Enable IP whitelisting |
| `VPN_SENTINEL_TLS_CERT_PATH` | ❌ | - | Path to TLS certificate for HTTPS |
| `VPN_SENTINEL_TLS_KEY_PATH` | ❌ | - | Path to TLS private key for HTTPS |
| `TELEGRAM_BOT_TOKEN` | ❌ | - | Telegram bot token for notifications |
| `TELEGRAM_CHAT_ID` | ❌ | - | Telegram chat ID for notifications |
| `VPN_SENTINEL_TELEGRAM_ENABLED` | ❌ | `false` | Enable Telegram notifications (auto-enabled if token provided) |
| `FLASK_ENV` | ❌ | `production` | Flask environment (`development`/`production`) |
| `TZ` | ❌ | `UTC` | System timezone |
| `LOG_LEVEL` | ❌ | `INFO` | Logging level (`DEBUG`/`INFO`/`WARNING`/`ERROR`) |

### **API Key Generation**

Generate a secure API key for authentication:

```bash
# Generate cryptographically secure 64-character hex key
VPN_SENTINEL_API_KEY=$(openssl rand -hex 32)
echo "API Key: ${VPN_SENTINEL_API_KEY}"
```

Use the same key for both client and server configuration.

## 🔧 Advanced Configuration

### **Multi-Client Setup**

Monitor multiple VPN connections with a single server:

```yaml
services:
  # VPN Client 1
  vpn-client-office:
    image: qmcgaw/gluetun:latest
    # ... VPN configuration ...

  # VPN Client 2
  vpn-client-home:
    image: qmcgaw/gluetun:latest
    # ... VPN configuration ...

  # Monitoring clients
  vpn-sentinel-client-office:
    image: agigante80/vpn-sentinel-client:latest
    network_mode: service:vpn-client-office
    environment:
      - VPN_SENTINEL_CLIENT_ID=office-vpn
      - VPN_SENTINEL_URL=http://vpn-sentinel-server:5000
      - VPN_SENTINEL_API_KEY=${API_KEY}

  vpn-sentinel-client-home:
    image: agigante80/vpn-sentinel-client:latest
    network_mode: service:vpn-client-home
    environment:
      - VPN_SENTINEL_CLIENT_ID=home-vpn
      - VPN_SENTINEL_URL=http://vpn-sentinel-server:5000
      - VPN_SENTINEL_API_KEY=${API_KEY}

  # Single monitoring server
  vpn-sentinel-server:
    image: agigante80/vpn-sentinel-server:latest
    # ... server configuration ...
```

### **VPN Provider Compatibility**

VPN Sentinel works with any Docker-based VPN client:

| VPN Client | Image | Network Mode |
|------------|-------|--------------|
| **Gluetun** | `qmcgaw/gluetun` | `service:vpn-client` |
| **OpenVPN** | `dperson/openvpn-client` | `service:vpn-client` |
| **WireGuard** | `linuxserver/wireguard` | `service:vpn-client` |
| **PIA WireGuard** | `thrnz/docker-wireguard-pia` | `service:vpn-client` |
| **Transmission+VPN** | `haugene/transmission-openvpn` | `service:vpn-client` |

### **Telegram Bot Setup**

1. **Create Bot**: Message [@BotFather](https://t.me/botfather) on Telegram
2. **Get Token**: `/newbot` → follow instructions → copy API token
3. **Get Chat ID**: Message your bot → visit `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. **Configure**: Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in server environment

## 📊 Monitoring & Health Checks

### **Health Check Endpoints**

VPN Sentinel provides comprehensive health monitoring:

```bash
# Server health
curl http://localhost:5000/api/v1/health

# Readiness check
curl http://localhost:5000/api/v1/health/ready

# Startup check
curl http://localhost:5000/api/v1/health/startup
```

### **Client Status Monitoring**

```bash
# Get all client statuses
curl -H "Authorization: Bearer ${API_KEY}" \
     http://localhost:5000/api/v1/status
```

### **Docker Health Checks**

Both client and server include Docker HEALTHCHECK instructions for automatic container health monitoring.

## � Web Dashboard

VPN Sentinel includes a modern, real-time web dashboard for visualizing your VPN connections and monitoring their health status.

### **Accessing the Dashboard**

The dashboard is available at:
```
http://your-server-ip:8080/dashboard
```

By default, the dashboard runs on **port 8080** and requires no authentication (configured via `VPN_SENTINEL_SERVER_DASHBOARD_PORT`).

### **Dashboard Features**

![VPN Sentinel Dashboard](docs/images/dashboard-screenshot.png)

The dashboard provides:

- **🖥️ Server Information**: Real-time server IP, location, provider, and DNS status
- **📊 Client Statistics**: Total clients, online count, offline count
- **🔄 Auto-Refresh**: Automatically updates every 30 seconds
- **📱 Responsive Design**: Works on desktop, tablet, and mobile devices

#### **Traffic Light Status System**

Each client displays a color-coded status indicator:

| Status | Color | Meaning | Action Required |
|--------|-------|---------|----------------|
| **🟢 Secure** | Green | VPN working correctly, no DNS leak | ✅ No action needed |
| **🟡 Warning** | Yellow | VPN active but DNS leak detected or unverifiable | ⚠️ Investigate DNS configuration |
| **🔴 Danger** | Red | **VPN BYPASS**: Client IP matches server IP | 🚨 **Immediate action required** |

#### **Client Information Table**

For each connected client, the dashboard shows:
- **Client ID**: Unique identifier for the VPN connection
- **VPN IP**: Public IP address as seen from the internet
- **Location**: City, region, and country of the VPN endpoint
- **Provider**: ISP or VPN provider name
- **Last Seen**: Time since last keepalive (e.g., "Just now", "5 min ago")
- **VPN Status**: Traffic light indicator (🟢/🟡/🔴)
- **DNS Leak**: DNS location and colocation server status

### **Dashboard Configuration**

Configure dashboard behavior with environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `VPN_SENTINEL_SERVER_DASHBOARD_PORT` | `8080` | Dashboard web server port |
| `VPN_SENTINEL_WEB_DASHBOARD_ENABLED` | `true` | Enable/disable web dashboard |
| `VPN_SENTINEL_VERSION` | `dev` | Version displayed in dashboard footer |

### **Dashboard URL Examples**

```bash
# Local development
http://localhost:8080/dashboard

# Remote server
http://192.168.1.100:8080/dashboard

# Domain with reverse proxy
https://vpn-monitor.example.com/dashboard
```

### **Reverse Proxy Configuration**

If exposing the dashboard through a reverse proxy (Nginx, Traefik, Caddy), ensure the dashboard port is proxied correctly:

```nginx
# Nginx example
location /dashboard {
    proxy_pass http://vpn-sentinel-server:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

## �📚 Documentation & Support

For detailed documentation, troubleshooting, API reference, and advanced configuration options, visit the [VPN Sentinel Wiki](https://github.com/agigante80/VPNSentinel/wiki).

### **Key Wiki Sections**
- [API Reference](https://github.com/agigante80/VPNSentinel/wiki/API-Reference) - Complete API documentation
- [Troubleshooting](https://github.com/agigante80/VPNSentinel/wiki/Troubleshooting) - Common issues and solutions
- [Deployment Patterns](https://github.com/agigante80/VPNSentinel/wiki/Deployment-Patterns) - Advanced deployment scenarios
- [Security](https://github.com/agigante80/VPNSentinel/wiki/Security) - Security hardening and best practices
- [Development](https://github.com/agigante80/VPNSentinel/wiki/Development) - Contributing and development setup

## ⚖️ License

**MIT License** - Open source with commercial usage permitted.

---

**VPN Sentinel** - Keep your VPN connections secure and monitored.
