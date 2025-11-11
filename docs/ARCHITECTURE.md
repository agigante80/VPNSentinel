# 🏗️ Architecture

## System Overview

VPN Sentinel uses a **distributed client-server architecture** designed for **network isolation** and scalability.

```
┌─────────────────────────────────────────────────────┐
│                   Host Machine                       │
│                                                      │
│  ┌───────────────────────────────────────────────┐ │
│  │        VPN Sentinel Server (Host Network)     │ │
│  │                                                │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐   │ │
│  │  │   API    │  │  Health  │  │Dashboard │   │ │
│  │  │  :5000   │  │  :8081   │  │  :8080   │   │ │
│  │  └──────────┘  └──────────┘  └──────────┘   │ │
│  │                                                │ │
│  │  ┌────────────────────────────────────────┐  │ │
│  │  │      Telegram Bot (Long Polling)       │  │ │
│  │  └────────────────────────────────────────┘  │ │
│  │                                                │ │
│  │  ┌────────────────────────────────────────┐  │ │
│  │  │    Client Monitoring (Background)      │  │ │
│  │  └────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────┘ │
│                         ▲                           │
│                         │ HTTP API                  │
│                         │                           │
│  ┌──────────────────────┴────────────────────────┐ │
│  │          VPN Client Container                  │ │
│  │                                                 │ │
│  │  ┌──────────────────────────────────────────┐ │ │
│  │  │   OpenVPN / WireGuard / gluetun          │ │ │
│  │  └──────────────────────────────────────────┘ │ │
│  │                         │                      │ │
│  │  ┌──────────────────────▼───────────────────┐ │ │
│  │  │  VPN Sentinel Client (Shared Network)    │ │ │
│  │  │  - Monitors VPN connectivity             │ │ │
│  │  │  - Sends keepalive to server             │ │ │
│  │  │  - Detects IP changes, DNS leaks         │ │ │
│  │  └──────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘

External Services:
  ├── Telegram Bot API (notifications)
  ├── ipinfo.io (geolocation, primary)
  ├── ip-api.com (geolocation, fallback)
  ├── Cloudflare (DNS leak detection)
  └── GitHub Container Registry / Docker Hub (images)
```

---

## Component Architecture

### 1. VPN Sentinel Server (`vpn-sentinel-server/`)

**Purpose**: Central monitoring hub, notification dispatcher, API provider

**Key Files**:
- `vpn-sentinel-server.py` - Main application with Flask multi-app server
- `Dockerfile` - Alpine-based Python 3.12 container image
- `health-monitor-wrapper.sh` - Wrapper script for health monitoring
- `health-monitor.py` - Health monitoring implementation

**Components**:

#### a) API App (Port 5000)
- **Authentication**: API key-based authentication
- **Rate Limiting**: 30 requests/minute per IP (configurable)
- **Endpoints**:
  - `POST /api/v1/keepalive` - Client keepalive with VPN status
  - `POST /api/v1/register` - Client registration (optional)
  - `GET /api/v1/status` - Server status
  - `GET /api/v1/clients` - List all clients

#### b) Health App (Port 8081)
- **Public Access**: No authentication required
- **Endpoints**:
  - `GET /health` - Simple health check (returns "OK")
  - `GET /healthz` - Kubernetes-style health check

#### c) Dashboard App (Port 8080)
- **Web Interface**: Real-time client monitoring
- **Features**:
  - Client status table
  - VPN connection details
  - Geolocation display
  - Last seen timestamps
  - Offline detection

#### d) Telegram Bot
- **Long Polling**: Receives commands from Telegram
- **Commands**:
  - `/start` - Initialize bot
  - `/status` - Show all clients status
  - `/help` - Show available commands
- **Notifications**:
  - VPN connection established
  - VPN disconnection detected
  - IP address changes
  - DNS leak detected
  - Client offline

#### e) Client Monitoring Thread
- **Background Process**: Checks client heartbeats
- **Timeout Detection**: Marks clients offline after threshold
- **Notifications**: Sends alerts when clients go offline

**Technology Stack**:
- **Language**: Python 3.12
- **Framework**: Flask 3.0.0
- **HTTP Library**: requests 2.31.0
- **Container**: Alpine Linux 3.18+

---

### 2. VPN Sentinel Client (`vpn-sentinel-client/`)

**Purpose**: VPN connectivity monitoring agent, runs inside VPN network

**Key Files**:
- `vpn-sentinel-client.py` - Python monitoring client (current)
- `vpn-sentinel-client.sh` - Legacy bash client (deprecated)
- `Dockerfile` - Alpine-based Python 3.12 container image
- `health-monitor.py` - Health monitoring implementation
- `health-monitor.sh` - Legacy health monitoring script
- `healthcheck.sh` - Docker healthcheck probe

**Capabilities**:
- Public IP detection (via ipinfo.io, ip-api.com)
- Geolocation lookup (country, city, region)
- DNS leak detection (via Cloudflare whoami.cloudflare + /cdn-cgi/trace)
- VPN status monitoring (via health scripts)
- Periodic keepalive to server
- Offline detection and recovery

**Network Isolation**:
```yaml
# Client runs in VPN container's network namespace
vpn-sentinel-client:
  network_mode: service:vpn-client  # Shares VPN network stack
  depends_on:
    - vpn-client
```

**Technology Stack**:
- **Language**: Python 3.12
- **HTTP Library**: requests 2.31.0
- **DNS Tools**: bind-tools (dig command)
- **Container**: Alpine Linux 3.18+

---

### 3. Common Library (`vpn_sentinel_common/`)

**Purpose**: Shared utilities between client and server

**Modules**:

- **`logging.py`**
  - Structured logging with component prefixes
  - Functions: `log_info()`, `log_warn()`, `log_error()`, `log_debug()`
  - Format: `[TIMESTAMP] [COMPONENT] MESSAGE`

- **`geolocation.py`**
  - IP geolocation with fallback providers
  - Primary: ipinfo.io (with optional API token)
  - Fallback: ip-api.com (free, no auth)
  - Functions: `get_location()`, `get_ip_details()`

- **`network.py`**
  - Network utilities and DNS detection
  - DNS trace parsing (Cloudflare format support)
  - Functions: `parse_dns_trace()`, `get_public_ip()`

---

## Data Flow

### Keepalive Flow

```
┌─────────────────┐
│  VPN Client     │
│  Container      │
└────────┬────────┘
         │
         │ 1. Check VPN status
         ▼
┌─────────────────┐
│ VPN Sentinel    │
│ Client          │
│                 │
│ 2. Get public   │
│    IP + geo     │
│ 3. DNS leak     │
│    detection    │
└────────┬────────┘
         │
         │ 4. POST /api/v1/keepalive
         │    {
         │      "client_id": "office-vpn",
         │      "public_ip": "1.2.3.4",
         │      "location": "US",
         │      "dns_loc": "US",
         │      "dns_colo": "SJC",
         │      "timestamp": "2025-01-15T12:00:00Z"
         │    }
         ▼
┌─────────────────┐
│ VPN Sentinel    │
│ Server          │
│                 │
│ 5. Update       │
│    client       │
│    registry     │
│                 │
│ 6. Detect       │
│    changes      │
└────────┬────────┘
         │
         │ 7. Send notification (if needed)
         │    - IP changed
         │    - DNS leak detected
         │    - Connection restored
         ▼
┌─────────────────┐
│  Telegram Bot   │
│  API            │
└─────────────────┘
```

### Notification Triggers

| Event | Condition | Notification |
|-------|-----------|--------------|
| **VPN Connected** | First keepalive after offline | "✅ VPN Connected!" |
| **IP Changed** | public_ip != previous_ip | "🔄 IP Address Changed" |
| **DNS Leak** | dns_loc != location | "⚠️ DNS LEAK DETECTED" |
| **Client Offline** | No keepalive for N seconds | "❌ Client Offline" |
| **VPN Bypass** | client_ip == server_ip | "⚠️ VPN BYPASS WARNING" |

---

## Storage & State Management

### In-Memory Storage

**Client Registry**:
```python
{
    "client_id": {
        "public_ip": "1.2.3.4",
        "location": "US",
        "city": "San Francisco",
        "dns_loc": "US",
        "dns_colo": "SJC",
        "last_seen": "2025-01-15T12:00:00Z",
        "status": "online",
        "vpn_connected": True
    }
}
```

**Rate Limiting State**:
```python
{
    "192.168.1.100": {
        "requests": [
            1705320000.123,
            1705320001.456,
            # ... timestamps
        ]
    }
}
```

**Limitations**:
- ❌ No persistence across restarts
- ❌ Single-server only (no replication)
- ❌ Memory usage grows with client count
- ✅ Fast access and updates
- ✅ Simple deployment (no database required)

---

## Configuration

### Environment Variables

#### Server Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `VPN_SENTINEL_SERVER_API_PORT` | `5000` | API app port |
| `VPN_SENTINEL_SERVER_HEALTH_PORT` | `8081` | Health app port |
| `VPN_SENTINEL_SERVER_DASHBOARD_PORT` | `8080` | Dashboard port |
| `VPN_SENTINEL_API_KEY` | `""` | API authentication key |
| `VPN_SENTINEL_API_PATH` | `/api/v1` | API base path |
| `VPN_SENTINEL_SERVER_RATE_LIMIT` | `30` | Requests per minute |
| `VPN_SENTINEL_SERVER_CHECK_INTERVAL` | `60` | Client check interval (seconds) |
| `VPN_SENTINEL_SERVER_OFFLINE_THRESHOLD` | `300` | Offline after N seconds |
| `VPN_SENTINEL_WEB_DASHBOARD_ENABLED` | `true` | Enable web dashboard |

#### Telegram Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `VPN_SENTINEL_TELEGRAM_TOKEN` | `""` | Bot token from @BotFather |
| `VPN_SENTINEL_TELEGRAM_CHAT_ID` | `""` | Target chat/user ID |
| `VPN_SENTINEL_TELEGRAM_ENABLED` | `false` | Enable Telegram notifications |

#### Client Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `VPN_SENTINEL_CLIENT_ID` | `"default-client"` | Unique client identifier |
| `VPN_SENTINEL_SERVER_URL` | `http://localhost:5000` | Server API URL |
| `VPN_SENTINEL_API_KEY` | `""` | API authentication key |
| `VPN_SENTINEL_API_PATH` | `/api/v1` | API base path |
| `VPN_SENTINEL_CHECK_INTERVAL` | `60` | Monitoring interval (seconds) |
| `VPN_SENTINEL_HEALTH_SCRIPT` | `""` | Custom health check script |
| `IPINFO_API_TOKEN` | `""` | ipinfo.io API token (optional) |

#### Security Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `VPN_SENTINEL_ALLOWED_IPS` | `""` | Comma-separated IP whitelist |
| `VPN_SENTINEL_SERVER_IP_WHITELIST_ENABLED` | `false` | Enable IP whitelisting |

---

## API Specification

### POST /api/v1/keepalive

**Purpose**: Client sends periodic keepalive with VPN status

**Authentication**: Required (API key)

**Request**:
```json
{
  "client_id": "office-vpn-primary",
  "public_ip": "203.0.113.42",
  "location": "US",
  "city": "San Francisco",
  "region": "California",
  "country": "United States",
  "dns_loc": "US",
  "dns_colo": "SJC",
  "vpn_connected": true,
  "timestamp": "2025-01-15T12:34:56Z"
}
```

**Response** (200 OK):
```json
{
  "status": "ok",
  "message": "Keepalive received",
  "server_time": "2025-01-15T12:34:56Z"
}
```

**Response** (401 Unauthorized):
```json
{
  "error": "Unauthorized",
  "message": "Invalid or missing API key"
}
```

**Response** (429 Too Many Requests):
```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Please wait before retrying.",
  "retry_after": 30
}
```

---

### GET /api/v1/clients

**Purpose**: List all registered clients

**Authentication**: Required (API key)

**Response** (200 OK):
```json
{
  "clients": [
    {
      "client_id": "office-vpn-primary",
      "public_ip": "203.0.113.42",
      "location": "US",
      "city": "San Francisco",
      "dns_loc": "US",
      "dns_colo": "SJC",
      "last_seen": "2025-01-15T12:34:56Z",
      "status": "online",
      "vpn_connected": true
    }
  ],
  "count": 1
}
```

---

### GET /health

**Purpose**: Simple health check (Kubernetes-compatible)

**Authentication**: Not required (public endpoint)

**Response** (200 OK):
```
OK
```

---

### GET /dashboard

**Purpose**: Web dashboard for monitoring clients

**Authentication**: Not required (public endpoint)

**Response** (200 OK):
```html
<!DOCTYPE html>
<html>
  <head><title>VPN Sentinel Dashboard</title></head>
  <body>
    <h1>VPN Sentinel Monitoring</h1>
    <table>
      <tr>
        <th>Client ID</th>
        <th>Status</th>
        <th>Public IP</th>
        <th>Location</th>
        <th>Last Seen</th>
      </tr>
      <!-- Dynamic client rows -->
    </table>
  </body>
</html>
```

---

## Security Architecture

### Authentication

- **API Key**: Required for `/api/v1/*` endpoints
- **Header**: `X-API-Key: your-api-key-here`
- **Validation**: Constant-time comparison to prevent timing attacks

### Rate Limiting

- **Algorithm**: Sliding window
- **Default**: 30 requests/minute per IP
- **Cleanup**: Automatic expiry of old entries
- **Bypass**: Health endpoints excluded

### Input Validation

- **Client ID**: Alphanumeric + hyphens only
- **IP Addresses**: IPv4/IPv6 format validation
- **Timestamps**: ISO 8601 format
- **Location**: String length limits

### Network Security

- **TLS**: Supported via reverse proxy (nginx, Traefik)
- **IP Whitelisting**: Optional firewall for API endpoints
- **Network Isolation**: Client runs in VPN network namespace

---

## Scalability Considerations

### Current Limitations

- **Single Server**: No horizontal scaling
- **In-Memory Storage**: No persistence or replication
- **Synchronous Processing**: No async workers
- **Single Telegram Bot**: Rate-limited by Telegram API

### Future Scalability

To scale VPN Sentinel:
1. **Add Database**: PostgreSQL/Redis for persistent storage
2. **Load Balancer**: Distribute API requests across servers
3. **Message Queue**: RabbitMQ/Redis for async notifications
4. **Sharding**: Partition clients across multiple servers
5. **Caching**: Redis for frequently accessed data

---

## Deployment Patterns

### Pattern 1: All-in-One

**Use Case**: Testing, single VPN monitoring

```yaml
services:
  vpn-client:
    image: qmcgaw/gluetun
    environment:
      - VPN_SERVICE_PROVIDER=nordvpn
    cap_add:
      - NET_ADMIN
  
  vpn-sentinel-client:
    image: ghcr.io/lcharles0/vpn-sentinel-client:latest
    network_mode: service:vpn-client
    depends_on:
      - vpn-client
      - vpn-sentinel-server
  
  vpn-sentinel-server:
    image: ghcr.io/lcharles0/vpn-sentinel-server:latest
    ports:
      - "5000:5000"
      - "8080:8080"
      - "8081:8081"
```

### Pattern 2: Client-Standalone

**Use Case**: Multiple VPN locations, central server

```yaml
# On each VPN location
services:
  vpn-client:
    image: qmcgaw/gluetun
  
  vpn-sentinel-client:
    image: ghcr.io/lcharles0/vpn-sentinel-client:latest
    network_mode: service:vpn-client
    environment:
      - VPN_SENTINEL_SERVER_URL=https://central-server.example.com:5000
      - VPN_SENTINEL_CLIENT_ID=location-1-vpn
```

### Pattern 3: Server-Central

**Use Case**: Central monitoring hub

```yaml
# Central server location
services:
  vpn-sentinel-server:
    image: ghcr.io/lcharles0/vpn-sentinel-server:latest
    ports:
      - "443:5000"  # Behind reverse proxy
      - "8080:8080"
    environment:
      - VPN_SENTINEL_TELEGRAM_ENABLED=true
      - VPN_SENTINEL_SERVER_OFFLINE_THRESHOLD=600
```

---

## Monitoring & Observability

### Health Checks

**Docker Health Check**:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8081/health || exit 1
```

**Kubernetes Liveness Probe**:
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8081
  initialDelaySeconds: 10
  periodSeconds: 30
```

### Logging

**Log Levels**:
- `INFO` - Normal operations (keepalive, connections)
- `WARN` - Suspicious activity (DNS leaks, bypasses)
- `ERROR` - Failures (API errors, Telegram send failures)
- `DEBUG` - Detailed tracing (DNS methods, HTTP calls)

**Log Format**:
```
[2025-01-15 12:34:56] [api] 🌐 Access: /api/v1/keepalive | IP: 1.2.3.4 | Auth: ✅
[2025-01-15 12:34:56] [security] ⚠️ VPN BYPASS WARNING: Client office-vpn has same IP as server
[2025-01-15 12:34:56] [telegram] ❌ Failed to send message: HTTP 429
```

---

## Technology Decisions

### Why Flask?

- ✅ Lightweight and fast for small-scale deployments
- ✅ Multi-app support (API, health, dashboard)
- ✅ Extensive middleware ecosystem
- ✅ Easy testing with test client
- ❌ Not ideal for high-concurrency async workloads

### Why Alpine Linux?

- ✅ Small image size (~50MB for client, ~80MB for server)
- ✅ Fast build and deployment
- ✅ Secure minimal attack surface
- ❌ Uses musl libc (compatibility issues with some Python packages)

### Why In-Memory Storage?

- ✅ Zero external dependencies
- ✅ Fast access (no I/O overhead)
- ✅ Simple deployment
- ❌ No persistence across restarts
- ❌ Not suitable for >1000 clients

### Why Python 3.12?

- ✅ Modern async/await support
- ✅ Improved error messages
- ✅ Performance improvements over 3.11
- ✅ Type hints and static analysis
- ✅ Excellent ecosystem for networking and HTTP

---

**Last Updated**: 2025-01-15  
**Version**: 1.0.0  
**Maintainer**: VPN Sentinel Team
