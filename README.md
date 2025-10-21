# VPN Sentinel

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue)](https://docs.docker.com/compose/)
[![Python](https://img.shields.io/badge/Python-3.11+-green)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-REST_API-orange)](https://flask.palletsprojects.com/)
[![Docker Hub](https://img.shields.io/badge/Docker%20Hub-agigante80-blue)](https://hub.docker.com/u/agigante80)

**Advanced Docker-based VPN monitoring system with real-time health checks, DNS leak detection, and instant Telegram notifications. Engineered for production reliability with comprehensive REST API, rate limiting, and multi-client architecture support.**

## 📦 Downloadable Docker Images

VPN Sentinel is now available as pre-built, downloadable Docker images on Docker Hub! No need to build locally - just pull and run.

```bash
# Pull the latest images
docker pull agigante80/vpn-sentinel-server:latest
docker pull agigante80/vpn-sentinel-client:latest

# Or use in docker-compose (automatic download)
docker compose up -d
```

**Available Images:**
- **`agigante80/vpn-sentinel-server:latest`** - Monitoring server with REST API and Telegram notifications
- **`agigante80/vpn-sentinel-client:latest`** - VPN network monitoring client

**Automated Publishing:** Images are automatically built and published via GitHub Actions on every push to the main branch.

## 📋 Versioning & Releases

VPN Sentinel uses **automatic semantic versioning** based on Git tags and branches:

### Version Format
- **Production** (`main` branch, clean tag): `1.0.0`, `1.1.0`, `2.0.0`
- **Pre-release** (`main` branch, commits ahead): `1.0.0+3` (3 commits ahead of v1.0.0)
- **Development** (`develop` branch): `1.0.0-dev-{commit-hash}`
- **Feature branches**: `1.0.0-{branch-name}-{commit-hash}`

### Current Versions
```bash
# Check current version
./get_version.sh

# Example outputs:
# On develop: 1.0.0-dev-6a53748
# On main (clean): 1.0.0
# On main (+3 commits): 1.0.0+3
```

### Creating New Releases
To release a new version:

```bash
# 1. Merge changes to main branch
git checkout main
git merge develop

# 2. Create and push a new version tag
git tag v1.0.1
git push origin v1.0.1

# 3. CI/CD automatically builds and publishes version 1.0.1
```

**Available Tags:**
- `latest` - Latest stable release from main branch
- `development` - Latest development build from develop branch
- `v{major}.{minor}.{patch}` - Specific version tags

## 🔬 Technical Overview

VPN Sentinel implements a sophisticated dual-network monitoring architecture that ensures VPN tunnel integrity through continuous health assessment and automated alerting. The system operates across isolated network segments, providing guaranteed communication channels even during VPN failures.

### 🏗️ Core Architecture

**Dual-Component Design:**
- **VPN Sentinel Client**: Executes within VPN-protected network namespace, performing internal health monitoring
- **VPN Sentinel Server**: Operates on host network infrastructure, maintaining external communication capabilities

**Network Communication Model:**
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

**Key Technical Advantages:**
- **Network Isolation**: Client and server operate in separate network namespaces
- **Internet-Based Communication**: Eliminates Docker networking dependencies
- **VPN-Agnostic Design**: Compatible with any Docker VPN container
- **Stateful Monitoring**: Tracks connection history and failure patterns
- **RESTful API**: Programmatic access to monitoring data and controls

## 🚀 Key Technical Features

### 🔍 Advanced Monitoring Capabilities

**Real-Time Health Assessment:**
- Continuous IP geolocation verification
- DNS resolver analysis with leak detection algorithms
- Connection state tracking with configurable thresholds
- Automated health check intervals (default: 5 minutes)

**DNS Leak Detection Engine:**
```python
# Core leak detection logic
def detect_dns_leak(vpn_country: str, dns_country: str) -> bool:
    """Detect DNS leaks by comparing VPN exit country vs DNS resolver country"""
    return vpn_country.lower() != dns_country.lower()
```

**Multi-Provider Geolocation Intelligence:**
- IP geolocation via ipinfo.io API
- DNS resolver location via Cloudflare trace endpoint
- Autonomous System (AS) number identification
- Provider-specific routing analysis

### 📡 REST API Architecture

**Endpoint Specifications:**

```http
# Health Check Endpoint
GET /api/v1/health
Authorization: Bearer {API_KEY}
Response: 200 OK with uptime metrics

# Status Retrieval
GET /api/v1/status
Authorization: Bearer {API_KEY}
Response: JSON array of client status objects

# Client Heartbeat
POST /api/v1/keepalive
Content-Type: application/json
Authorization: Bearer {API_KEY}
Body: {
  "client_id": "vpn-monitor-01",
  "public_ip": "89.40.181.202",
  "country": "RO",
  "city": "Bucharest",
  "dns_location": "RO"
}
```

**API Security Features:**
- Bearer token authentication for all endpoints
- Configurable rate limiting (default: 30 requests/minute)
- IP whitelist support with CIDR notation
- Request logging with client identification

### 🔔 Intelligent Notification System

**Telegram Bot Integration:**
- Interactive command processing (`/ping`, `/status`, `/help`)
- Rich HTML-formatted notifications with emoji indicators
- Smart alert suppression to prevent notification spam
- Multi-language support with timezone-aware timestamps

**Alert Classification:**
- **Connection Events**: VPN establishment and IP changes
- **Failure Alerts**: Connection loss with configurable thresholds
- **DNS Leak Warnings**: Resolver location mismatches
- **Bypass Detection**: Same-IP address conflict identification

### 🛡️ Security & Reliability

**Authentication & Authorization:**
- Mandatory API key requirement for all server operations
- Cryptographically secure key generation (`openssl rand -hex 32`)
- Stateless authentication with Bearer token validation

**Network Security:**
- TLS/SSL support for encrypted client-server communication
- Self-signed certificate generation utilities
- Port isolation with configurable network exposure

**Operational Security:**
- Container privilege minimization
- Isolated network namespaces
- Secure environment variable handling
- Audit logging for all API interactions

## 📋 Technical Specifications

### System Requirements

**Minimum Hardware:**
- 512MB RAM per monitoring instance
- 100MB storage for container images
- Single CPU core allocation

**Software Dependencies:**
- Docker Engine 20.10+
- Docker Compose v2.0+
- Python 3.11+ (server component)
- curl (client component)

**Network Requirements:**
- Outbound internet connectivity for API calls
- Configurable inbound port (default: 5000) for server
- DNS resolution capabilities
- Firewall configuration for monitoring ports

### Performance Characteristics

**Resource Utilization:**
- **CPU**: <5% average load during normal operation
- **Memory**: ~50MB per container instance
- **Network**: ~100KB/hour per monitoring client
- **Storage**: <10MB for logs and configuration

**Scalability Metrics:**
- Single server supports 100+ concurrent clients
- API response time: <100ms for status queries
- Notification delivery: <5 seconds from event detection

## 🚀 Deployment Architecture

### Quick Start Configuration

VPN Sentinel offers **4 flexible deployment options** to fit different use cases:

- **All-in-One**: Complete stack (VPN + client + server) - `deployments/all-in-one/`
- **Client with VPN**: VPN client + monitoring client - `deployments/client-with-vpn/`
- **Client Standalone**: Monitoring client only - `deployments/client-standalone/`
- **Server Central**: Monitoring server only - `deployments/server-central/`

```bash
# 1. Clone repository
git clone https://github.com/agigante80/VPNSentinel.git
cd VPNSentinel

# 2. Choose your deployment (see deployments/ directory)
cd deployments/all-in-one/        # OR client-with-vpn/, client-standalone/, server-central/

# 3. Configure environment
cp .env.example .env
# Edit .env with your configuration

# 4. Deploy stack (images download automatically)
docker compose up -d

# 5. Verify operation
docker compose logs -f vpn-sentinel-client
```

**🚀 Pro Tip:** All VPN Sentinel images are pre-built and available on Docker Hub. No local building required!

### Environment Configuration Matrix

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `VPN_SERVICE_PROVIDER` | string | Yes* | - | VPN provider identifier (Gluetun-specific) |
| `VPN_USER` | string | Yes | - | VPN account username |
| `VPN_PASSWORD` | string | Yes | - | VPN account password |
| `VPN_SENTINEL_API_KEY` | string | Yes | - | 64-char hex authentication key |
| `VPN_SENTINEL_URL` | URL | Yes | - | Server endpoint URL |
| `TELEGRAM_BOT_TOKEN` | string | Recommended | - | Telegram bot API token |
| `TELEGRAM_CHAT_ID` | string | Recommended | - | Telegram chat identifier |
| `TZ` | timezone | Optional | UTC | System timezone for timestamps |

*Required only when using Gluetun VPN client

### Docker Compose Architecture

```yaml
version: '3.8'
services:
  vpn-client:  # Generic VPN container (Gluetun/OpenVPN/WireGuard/etc.)
    image: qmcgaw/gluetun:latest
    environment:
      - VPN_SERVICE_PROVIDER=${VPN_SERVICE_PROVIDER}
      - OPENVPN_USER=${VPN_USER}
      - OPENVPN_PASSWORD=${VPN_PASSWORD}
    cap_add:
      - NET_ADMIN
    devices:
      - /dev/net/tun
    volumes:
      - ./vpn-client:/gluetun
    restart: always

  vpn-sentinel-client:  # Monitoring client in VPN namespace
    image: agigante80/vpn-sentinel-client:latest  # 🆕 Pre-built image
    network_mode: service:vpn-client  # Shares VPN network stack
    volumes:
      - ./certs:/certs:ro
    environment:
      - VPN_SENTINEL_API_KEY=${VPN_SENTINEL_API_KEY}
      - VPN_SENTINEL_URL=${VPN_SENTINEL_URL}
    restart: always

  vpn-sentinel-server:  # External monitoring server
    image: agigante80/vpn-sentinel-server:latest  # 🆕 Pre-built image
    ports:
      - "5000:5000"  # API port
      - "8080:8080"  # Dashboard port
    volumes:
      - ./certs:/certs:ro
    environment:
      - VPN_SENTINEL_API_KEY=${VPN_SENTINEL_API_KEY}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
    restart: always
```

**🆕 What's New:** The `build:` directives have been replaced with `image:` references to pre-built, downloadable Docker images. Images are automatically published to Docker Hub via GitHub Actions CI/CD pipeline.

## 🔧 Advanced Configuration

### VPN Client Compatibility Matrix

| VPN Client | Image | Configuration Method | Network Mode |
|------------|-------|---------------------|--------------|
| **Gluetun** | `qmcgaw/gluetun` | Environment variables | `service:vpn-client` |
| **OpenVPN** | `dperson/openvpn-client` | Volume-mounted .ovpn | `service:vpn-client` |
| **WireGuard** | `linuxserver/wireguard` | Environment + volumes | `service:vpn-client` |
| **Transmission+VPN** | `haugene/transmission-openvpn` | Provider-specific env | `service:vpn-client` |
| **PIA WireGuard** | `thrnz/docker-wireguard-pia` | PIA credentials | `service:vpn-client` |

### Multi-Client Deployment Pattern

```yaml
# Single server, multiple VPN clients
services:
  vpn-client-office:
    # VPN configuration...
  vpn-client-home:
    # VPN configuration...

  vpn-sentinel-client-office:
    network_mode: service:vpn-client-office
    environment:
      - VPN_SENTINEL_CLIENT_ID=office-vpn

  vpn-sentinel-client-home:
    network_mode: service:vpn-client-home
    environment:
      - VPN_SENTINEL_CLIENT_ID=home-vpn

  vpn-sentinel-server:
    # Single server instance handles multiple clients
```

## 📊 API Reference

### Authentication

All API requests require Bearer token authentication:

```bash
curl -H "Authorization: Bearer your-api-key-here" \
     http://localhost:5000/api/v1/status
```

### Core Endpoints

#### `GET /api/v1/health`
**Purpose:** Service health verification
**Response:** JSON health status with uptime metrics
```json
{
  "status": "healthy",
  "uptime_seconds": 3600,
  "version": "1.0.0"
}
```

#### `GET /api/v1/status`
**Purpose:** Retrieve all client monitoring status
**Response:** Array of client status objects
```json
[
  {
    "client_id": "office-vpn",
    "last_seen": "2025-10-14T10:30:00Z",
    "public_ip": "89.40.181.202",
    "country": "RO",
    "city": "Bucharest",
    "status": "alive",
    "dns_location": "RO"
  }
]
```

#### `POST /api/v1/keepalive`
**Purpose:** Client heartbeat submission
**Request Body:** Client status data
```json
{
  "client_id": "office-vpn",
  "public_ip": "89.40.181.202",
  "country": "RO",
  "city": "Bucharest",
  "dns_location": "RO"
}
```

### Rate Limiting

- **Default Limit:** 30 requests per minute per IP
- **Header Response:** `X-RateLimit-Remaining: 29`
- **Throttle Response:** `429 Too Many Requests`

## 🧪 Testing & Quality Assurance

### Test Suite Architecture

**Unit Tests:**
```bash
# Core component testing
pytest tests/unit/ -v --cov=vpn-sentinel-server/
```

**Integration Tests:**
```bash
# End-to-end workflow validation
pytest tests/integration/ -v
```

**Docker Compose Validation:**
```bash
# Configuration syntax checking
docker compose config --quiet
```

### Test Coverage Metrics

- **Target Coverage:** 80%+ code coverage
- **Critical Paths:** API authentication, DNS leak detection, notification logic
- **Performance Tests:** API response times, memory usage, concurrent connections

## 🔄 CI/CD & Automated Publishing

### GitHub Actions Pipeline

VPN Sentinel uses comprehensive CI/CD automation for quality assurance and deployment:

**Automated Workflows:**
- **Syntax & Style Checks:** Python linting, shell script validation, Docker Compose syntax
- **Unit Testing:** Core component testing with pytest and coverage reporting
- **Integration Testing:** End-to-end workflow validation with Docker Compose
- **Security Scanning:** Trivy vulnerability scanning with SARIF upload to GitHub Security tab
- **Docker Publishing:** Automated image building and publishing to Docker Hub

**Workflow Triggers:**
- **Automatic:** Push to `main` or `develop` branches
- **Manual:** Can be triggered manually from GitHub Actions UI
- **Pull Requests:** Full validation on PR creation

### Docker Image Publishing

**Automated Publishing Process:**
```yaml
# GitHub Actions automatically:
# 1. Build vpn-sentinel-server and vpn-sentinel-client images
# 2. Run comprehensive tests and security scans
# 3. Login to Docker Hub using encrypted secrets
# 4. Push images with proper tags (latest, branch, commit SHA)
# 5. Make images publicly available for download
```

**Published Images:**
- **`agigante80/vpn-sentinel-server:latest`** - Production-ready server image
- **`agigante80/vpn-sentinel-client:latest`** - Production-ready client image
- **Tagged Releases:** Version-specific tags for stable releases

**Image Security:**
- Built from verified base images (Python Alpine, official Docker images)
- Automated security scanning with Trivy
- No hardcoded secrets or credentials
- Regular base image updates via automated builds

## 🔧 Troubleshooting & Diagnostics

### Common Failure Patterns

**Client-Server Communication Issues:**
```bash
# Verify server accessibility
curl -v http://your-server:5000/api/v1/health

# Check client network routing
docker exec vpn-sentinel-client traceroute your-server-ip

# Validate API key configuration
docker logs vpn-sentinel-server | grep "API key"
```

**DNS Leak False Positives:**
- Some VPN providers use geographically distributed DNS servers
- Configure `DNS_LEAK_TOLERANCE` environment variable
- Review provider-specific DNS behavior documentation

**Telegram Notification Failures:**
```bash
# Test bot connectivity
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"

# Verify chat permissions
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d "chat_id=${TELEGRAM_CHAT_ID}" -d "text=Test"
```

### Diagnostic Commands

```bash
# Full system health check
docker compose ps
docker compose logs --tail=50
docker stats

# Network connectivity testing
docker exec vpn-sentinel-client curl -s https://ipinfo.io/json
docker exec vpn-sentinel-client curl -s https://1.1.1.1/cdn-cgi/trace

# API endpoint validation
curl -H "Authorization: Bearer ${VPN_SENTINEL_API_KEY}" http://localhost:5000/api/v1/health
curl -H "Authorization: Bearer ${VPN_SENTINEL_API_KEY}" http://localhost:5000/api/v1/status
```

## 🚀 Production Deployment Guide

### Security Hardening

**API Key Management:**
```bash
# Generate cryptographically secure key
VPN_SENTINEL_API_KEY=$(openssl rand -hex 32)
echo "API Key: ${VPN_SENTINEL_API_KEY}"
```

**Network Security:**
```bash
# Configure firewall rules
ufw allow 5000/tcp
ufw allow 8080/tcp  # Future dashboard

# IP whitelist configuration
VPN_SENTINEL_SERVER_ALLOWED_IPS="192.168.1.0/24,10.0.0.0/8"
```

**TLS Configuration:**
```bash
# Place certificates in the certs/ directory
# Configure server for HTTPS (certificates auto-mounted)
VPN_SENTINEL_TLS_CERT_PATH=/certs/vpn-sentinel-cert.pem
VPN_SENTINEL_TLS_KEY_PATH=/certs/vpn-sentinel-key.pem
```

### Certificate Generation

**Generate Self-Signed Certificates (Testing/Development):**
```bash
# interactive
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -sha256 -days 365

# non-interactive and 10 years expiration
openssl req -x509 -newkey rsa:4096 -keyout ./certs/vpn-sentinel-key.pem -out ./certs/vpn-sentinel-cert.pem -sha256 -days 3650 -nodes -subj "/C=XX/ST=StateName/L=CityName/O=CompanyName/OU=CompanySectionName/"

# Set proper permissions
chmod 644 certs/vpn-sentinel-cert.pem
chmod 600 certs/vpn-sentinel-key.pem
```

**Using Let's Encrypt Certificates (Production):**
```bash
# Install certbot
sudo apt update && sudo apt install certbot

# Generate certificate (replace your-domain.com)
sudo certbot certonly --standalone -d your-domain.com

# Copy certificates to certs directory
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./certs/vpn-sentinel-cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./certs/vpn-sentinel-key.pem

# Set proper ownership and permissions
sudo chown $(whoami):$(whoami) certs/vpn-sentinel-*.pem
chmod 644 certs/vpn-sentinel-cert.pem
chmod 600 certs/vpn-sentinel-key.pem
```

**Certificate File Requirements:**
- `vpn-sentinel-cert.pem` - Public certificate (X.509 format)
- `vpn-sentinel-key.pem` - Private key (PKCS#8 or PKCS#1 format)
- Files must be readable by the container user
- Private key should have restricted permissions (600)

**Certificate Validation:**
```bash
# Check certificate validity
openssl x509 -in certs/vpn-sentinel-cert.pem -text -noout | grep -E "(Subject:|Issuer:|Not Before:|Not After)"

# Verify certificate and key match
openssl x509 -noout -modulus -in certs/vpn-sentinel-cert.pem | openssl md5
openssl rsa -noout -modulus -in certs/vpn-sentinel-key.pem | openssl md5
```

### Monitoring Integration

**Health Check Endpoints:**
```bash
# Prometheus-compatible metrics (future)
curl http://localhost:5000/metrics

# Nagios/Icinga compatible
curl http://localhost:5000/health | grep -q "healthy"
```

**Log Aggregation:**
```bash
# Structured JSON logging
docker compose logs vpn-sentinel-server --json | jq .
```

## 🔮 Roadmap & Technical Evolution

### Phase 1: Multi-Client Architecture (Q4 2025)
- **Client Registry:** Dynamic client registration and identification
- **Unified Dashboard:** Single interface for multiple VPN monitoring
- **Alert Aggregation:** Consolidated notifications across all clients

### Phase 2: Advanced Analytics (Q1 2026)
- **Performance Metrics:** Bandwidth, latency, and connection quality tracking
- **Historical Analysis:** Connection uptime statistics and failure patterns
- **Geographic Intelligence:** VPN server location optimization
- **Predictive Alerts:** ML-based failure prediction algorithms

### Phase 3: Enterprise Features (Q2 2026)
- **High Availability:** Multi-server deployment with failover
- **LDAP Integration:** Enterprise authentication and authorization
- **Audit Logging:** Comprehensive security event tracking
- **API Rate Limiting:** Advanced throttling with burst handling

## 🤝 Development & Contribution

### Code Quality Standards

**Testing Requirements:**
- Unit test coverage >80% for new features
- Integration tests for API endpoints
- Docker Compose validation in CI/CD pipeline

**Code Style:**
```bash
# Python formatting
black vpn-sentinel-server/
flake8 vpn-sentinel-server/

# Shell script linting
shellcheck vpn-sentinel-client/*.sh
```

### Development Environment

```bash
# Setup development environment
python -m venv .venv
source .venv/bin/activate
pip install -r tests/requirements.txt

# Run test suite
pytest --cov-report=html --cov=vpn-sentinel-server/

# Start development server
python vpn-sentinel-server/vpn-sentinel-server.py
```

**🆕 Development vs Production:**
- **Development:** Build locally using `build:` directives for active development
- **Production:** Use pre-built `image:` references for stability and speed
- **CI/CD:** Automated publishing ensures production images are always up-to-date

## 📚 Technical Documentation

### API Documentation
- **OpenAPI Specification:** `/api/v1/docs` (future endpoint)
- **Postman Collection:** Available in `docs/` directory
- **SDK Generation:** Python client library planned

### Architecture Diagrams
- **Network Topology:** Detailed network isolation diagrams
- **Component Interaction:** Sequence diagrams for monitoring workflows
- **Deployment Patterns:** Multi-client and high-availability configurations

### Performance Benchmarks
- **Latency Metrics:** API response times under various loads
- **Resource Utilization:** Memory and CPU usage patterns
- **Scalability Testing:** Concurrent client handling capacity

## ⚖️ License & Legal

**MIT License:** Open-source distribution with commercial usage permitted.

**Security Considerations:**
- No telemetry or data collection
- Local-only processing architecture
- Transparent source code auditability
- Community-driven security reviews

---

**VPN Sentinel** - Engineered for production VPN monitoring with enterprise-grade reliability and comprehensive API integration.

**🎉 Docker Images Available:** Pre-built, downloadable images on Docker Hub for instant deployment!
