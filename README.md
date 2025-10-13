# VPN Sentinel 🔒🚨
*Advanced VPN Monitoring & DNS Leak Detection with Telegram Notifications*

A comprehensive Docker-based solution for monitoring VPN connections, detecting DNS leaks, and providing instant Telegram notifications when your VPN fails or changes. Perfect for monitoring any VPN-protected Docker network and ensuring your privacy is never compromised.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue)](https://docs.docker.com/compose/)
[![VPN](https://img.shields.io/badge/VPN-Monitoring-green)](https://github.com/qdm12/gluetun)

## 🚨 **What is VPN Sentinel?**

VPN Sentinel is a dual-system monitoring solution that ensures your VPN-protected containers never expose your real IP address. It combines **inside-VPN monitoring** with **outside-VPN reporting** and **instant Telegram notifications** to create an unbreakable chain of protection.

### 🎯 **The Problem We Solve**

When VPN containers fail, your applications often continue running but **leak your real IP address** without any warning. Traditional monitoring solutions either:
- ❌ Run inside the VPN (can't report when VPN fails)
- ❌ Run outside the VPN (can't detect what's happening inside)
- ❌ Don't provide real-time notifications
- ❌ Don't detect DNS leaks

**VPN Sentinel solves ALL of these problems with a revolutionary dual-system approach.**

### 🔄 **VPN Client Agnostic Design**

VPN Sentinel works with **ANY Docker VPN client**:
- ✅ **Gluetun** (our example - 70+ providers)
- ✅ **OpenVPN** clients (custom configurations)
- ✅ **WireGuard** containers (modern protocol)  
- ✅ **Transmission+VPN** (integrated solutions)
- ✅ **Commercial VPN containers** (NordVPN, PIA, etc.)
- ✅ **Your existing VPN setup** - whatever you're already using!

> **🎯 Key Point**: We use **Gluetun as our example** because it's popular and supports many providers, but VPN Sentinel is designed to work with **any VPN container** you prefer!

### 🛡️ **Dual-System Architecture: Inside + Outside**

**🔍 VPN Sentinel Client (Inside VPN Network):**
- Monitors VPN connection health from within the protected network
- Performs continuous DNS leak detection using Cloudflare's trace endpoint
- Tests IP geolocation and provider information every 5 minutes
- **Communicates with server over internet via VPN connection** (not internal network)
- Sends encrypted status reports to the external monitoring server
- Detects when DNS requests leak outside the VPN tunnel

**📡 VPN Sentinel Server (Outside VPN Network):**
- Receives status reports from VPN clients **via internet connection**
- **Requires open port (default: 5000) to receive client reports**
- Maintains communication even when VPN fails completely
- Sends instant Telegram notifications for any status changes
- Provides REST API endpoints for external integrations
- Tracks client health and sends alerts after configurable thresholds

> **🌐 Important Network Architecture:** The client connects to the server **over the internet through the VPN tunnel**, not via Docker's internal networking. This is why the server port must be accessible from the internet and why monitoring works even with different VPN providers.

**📱 Telegram Notification System:**
- **Instant mobile alerts** - Get notified within seconds of any issue
- **Interactive bot commands** - `/ping`, `/status`, `/help` for remote monitoring
- **Rich notifications** - Detailed IP, location, DNS status in every alert
- **Real-time status updates** - Connection established, IP changes, failures

## ✨ **Key Features**

### 🔒 **Advanced VPN Monitoring**
- **Continuous Health Checks**: 5-minute intervals with instant failure detection
- **DNS Leak Detection**: Compares VPN exit country with DNS resolver location
- **IP Change Tracking**: Instant notifications when VPN server switches
- **Geolocation Monitoring**: Tracks city, region, country, provider, timezone
- **Connection Status**: Real-time alive/dead status with customizable thresholds

### 📱 **Telegram Integration**
- **Interactive Bot**: `/ping` test connectivity, `/status` get detailed info, `/help` for commands
- **Rich Notifications**: HTML-formatted messages with all relevant details
- **Smart Alerting**: Prevents notification spam with intelligent state tracking
- **Mobile Ready**: Get alerts anywhere, anytime on your phone

### � **Security & Reliability**
- **Rate Limiting**: Prevents abuse with configurable per-IP limits
- **API Authentication**: Optional API key protection for endpoints
- **IP Whitelisting**: Restrict access to trusted networks only
- **Network Isolation**: Server runs independently from VPN for guaranteed communication
- **Failure Recovery**: Automatic reconnection and status recovery

### 🌐 **Network Requirements**
- **Open Port Required**: Server port 5000 must be accessible from internet
- **Internet Communication**: Client connects to server via VPN tunnel over internet
- **No Internal Networking**: Client and server don't use Docker's internal networks
- **Firewall Configuration**: Ensure port 5000 is open in your firewall/router
- **VPN Compatibility**: Works with any VPN because communication is over internet

### 🔌 **Easy Integration**
- **Universal Compatibility**: Works with ANY VPN container (Gluetun, OpenVPN, WireGuard, etc.)
- **Docker Compose Ready**: Simple integration with existing stacks
- **Synology NAS Compatible**: Tested and working on Synology DSM with Container Manager
- **REST API**: `/status`, `/health`, `/keepalive` endpoints for external systems
- **Minimal Dependencies**: Lightweight containers with small resource footprint

## 🚀 **Quick Start**

### Prerequisites
- Docker and Docker Compose installed
- **ANY VPN client container** (we include Gluetun as an example with 70+ providers)
- VPN provider account
- Telegram bot token (optional, but highly recommended)

> **🔄 Important:** Gluetun is just our **example VPN client**. VPN Sentinel works with **ANY Docker VPN solution** - simply change the container name in the configuration!

> **🏠 Synology NAS Tested:** This solution has been **successfully tested and works on Synology NAS systems**. Despite Synology's Docker implementation being notoriously challenging, VPN Sentinel's internet-based architecture bypasses common Synology networking issues. The system works reliably on Synology DSM with Docker and Container Manager.

### 1. **Get Telegram Bot Token (Recommended)**
```bash
# 1. Message @BotFather on Telegram
# 2. Send: /newbot
# 3. Follow prompts to create your bot
# 4. Save the bot token

# 5. Get your Chat ID from @userinfobot
# 6. Message @userinfobot and save your chat ID
```

### 2. **Clone and Configure**
```bash
# Clone repository
git clone https://github.com/your-username/vpn-sentinel.git
cd vpn-sentinel

# Create environment file
cp .env.example .env
nano .env  # Add your VPN credentials and Telegram settings
```

### 3. **Environment Configuration (.env)**
```bash
# VPN Settings (example for Gluetun + PrivateVPN - change to your provider/client)
VPN_SERVICE_PROVIDER=privatevpn     # Only needed for Gluetun
VPN_USER=your_vpn_username          # Adapt based on your VPN client
VPN_PASSWORD=your_vpn_password      # Adapt based on your VPN client  
SERVER_COUNTRIES=Switzerland,Netherlands  # Only needed for Gluetun

# Telegram Notifications (highly recommended)
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHAT_ID=your_chat_id_from_userinfobot

# VPN Sentinel Configuration
KEEPALIVE_SERVER_URL=http://keepalive-server:5000  # Client reaches server via internet
KEEPALIVE_CLIENT_ID=vpn-monitor-main               # Unique identifier for this client
KEEPALIVE_API_KEY=your-secure-random-key           # Secure API communication

# System Settings
TZ=Europe/London
PUID_MEDIA=1000
PGID_MEDIA=1000
```

### 4. **Deploy the Stack**
```bash
# Start all services
docker compose up -d

# Check status
docker compose ps

# Watch logs
docker compose logs -f keepalive-client
docker compose logs -f keepalive-server
```

## 📊 **How to Use**
### 🎯 **Access Points**
| Service | URL | Purpose |
|---------|-----|---------|
| **Keepalive Server API** | http://your-server:5000 | Monitor VPN status, health checks |
| **VPN Client Container** | - | Your VPN container (any Docker VPN solution) |

### 📱 **Telegram Bot Commands**
Once your Telegram bot is configured, use these commands:

- **`/ping`** - Test bot connectivity and get server info  
- **`/status`** - Get detailed VPN client status and health
- **`/help`** - Show all available commands and features

## 🔧 **Advanced Configuration**

### 📝 **Complete Environment Variables (.env)**
```bash
# =============================================================================
# VPN Configuration (Example: PrivateVPN - Change to your provider)
# =============================================================================
VPN_SERVICE_PROVIDER=privatevpn      # Your VPN provider name
VPN_USER=your_vpn_username           # VPN account username
VPN_PASSWORD=your_vpn_password       # VPN account password
SERVER_COUNTRIES=Switzerland,Netherlands  # Preferred VPN server countries
UPDATER_PERIOD=24h                   # How often to check for VPN updates

# =============================================================================  
# Telegram Notification Settings (Highly Recommended)
# =============================================================================
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGhIjKlMnOpQrStUvWxYz  # From @BotFather
TELEGRAM_CHAT_ID=123456789           # Your chat ID from @userinfobot

# =============================================================================
# VPN Sentinel Configuration
# =============================================================================
KEEPALIVE_SERVER_URL=http://keepalive-server:5000  # Client connects via internet (through VPN)
KEEPALIVE_CLIENT_ID=vpn-monitor-main                # Unique client identifier
KEEPALIVE_API_KEY=your-secure-random-key-here       # API security key

# Security & Rate Limiting
MAX_REQUESTS_PER_MINUTE=30           # Rate limit per IP (prevent abuse)
ALLOWED_IPS=                         # Comma-separated IP whitelist (optional)

# =============================================================================
# System Configuration
# =============================================================================
TZ=Europe/London                     # Your timezone
PUID_MEDIA=1000                      # User ID for file permissions
PGID_MEDIA=1000                      # Group ID for file permissions
VOLUME_DOCKER_PROJECT=/opt/vpn-sentinel  # Docker config directory
```

### 🔄 **Add to Existing VPN Setup**

Already have a VPN-protected Docker stack? Add VPN Sentinel monitoring in 3 steps:

```yaml
# Add to your existing docker-compose.yaml
version: '3.8'
services:
  # Your existing VPN container (keep as-is)
  your-vpn-container:
    # ... your existing VPN config ...

  # Add VPN Sentinel monitoring
  keepalive-server:
    image: python:3.11-alpine
    container_name: vpn-sentinel-server
    ports:
      - "5000:5000"
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
      - KEEPALIVE_API_KEY=${KEEPALIVE_API_KEY}
      - TZ=${TZ}
    volumes:
      - ./keepalive-server/keepalive-server.py:/app/keepalive-server.py:ro
    working_dir: /app
    command: >
      sh -c "pip install flask requests pytz && python keepalive-server.py"
    restart: unless-stopped

  vpn-sentinel-client:
    image: curlimages/curl:latest
    container_name: vpn-sentinel-client
    environment:
      - KEEPALIVE_SERVER_URL=http://your-server-ip:5000  # Use your actual server IP!
      - KEEPALIVE_CLIENT_ID=your-client-name
      - KEEPALIVE_API_KEY=${KEEPALIVE_API_KEY}
      - TZ=${TZ}
    volumes:
      - ./keepalive-client/keepalive-client.sh:/tmp/keepalive-client.sh:ro
    network_mode: service:vpn-client  # Routes through your VPN tunnel
    command: >
      sh -c "sleep 30 && cp /tmp/keepalive-client.sh /home/curl_user/keepalive-client.sh && 
             chmod +x /home/curl_user/keepalive-client.sh && 
             exec /home/curl_user/keepalive-client.sh"
    depends_on:
      - your-vpn-container
    restart: unless-stopped

# Note: Client connects to server over internet, not Docker internal network!
# Make sure to replace 'your-server-ip' with your actual server's IP address.
```

## 📊 **Monitoring Dashboard**

### 🌐 **API Endpoints**
VPN Sentinel provides REST API endpoints for integration with monitoring tools:

```bash
# Get current VPN status (JSON response) - requires API key
curl -H "Authorization: Bearer your-api-key-here" http://your-server:5000/status

# Health check (uptime monitoring) - requires API key
curl -H "Authorization: Bearer your-api-key-here" http://your-server:5000/health

# Test heartbeat (for debugging) - requires API key
curl -X POST http://your-server:5000/fake-heartbeat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key-here" \
  -d '{"client_id": "test", "public_ip": "1.2.3.4"}'
```

### 📈 **Example Status Response**
```json
{
  "vpn-monitor-main": {
    "last_seen": "2025-10-13T14:30:15+00:00",
    "minutes_ago": 2,
    "public_ip": "89.40.181.202",
    "status": "alive"
  }
}
```

### 🔔 **Notification Examples**

**✅ VPN Connected:**
```
✅ VPN Connected!

Client: vpn-monitor-main
VPN IP: 89.40.181.202
📍 Location: Bucharest, București, RO
🏢 Provider: AS9009 M247 Europe SRL
🕒 VPN Timezone: Europe/Bucharest
Connected at: 2025-10-13 14:30:15 UTC

🔒 DNS Leak Test:
DNS Location: RO
DNS Server: OTP
✅ No DNS leak detected
```

**❌ VPN Failed:**
```
❌ VPN Connection Lost!

Client: vpn-monitor-main
Last IP: 89.40.181.202
📍 Last Location: Bucharest, București, RO
🏢 Provider: AS9009 M247 Europe SRL
⏰ Last seen: 18 minutes ago
🕐 Last contact: 2025-10-13 14:12:15 UTC
⚠️ Lost at: 2025-10-13 14:30:15 UTC

🔒 Last DNS Status:
DNS Location: RO
DNS Server: OTP
✅ No DNS leak was detected
```

## 🛡️ **VPN Sentinel Architecture**

### 🏗️ **Network Architecture Diagram**
```
┌─────────────────────────────────────────────────────────────────────┐
│                         🌍 INTERNET                                │
│                                                                     │
│  ┌──────────────────────┐          ┌──────────────────────────────┐ │
│  │    🏠 YOUR SERVER    │          │     🌐 VPN PROVIDER          │ │
│  │    (Real IP)         │          │     (VPN Server)             │ │
│  │                      │          │                              │ │
│  │  ┌─────────────────┐ │          └──────────────────────────────┘ │
│  │  │ 🔒 VPN Container│◄┼─────────────────VPN TUNNEL──────────────── │
│  │  │   (VPN IP)      │ │                      ▲                   │
│  │  │                 │ │                      │                   │
│  │  │  ┌────────────┐ │ │                      │                   │
│  │  │  │📡 CLIENT   │ │ │           🌐 INTERNET CONNECTION           │
│  │  │  │• Monitors  │ │ │           (via VPN tunnel)               │
│  │  │  │• DNS Tests │ │ │                      │                   │
│  │  │  │• Reports   │ │ │                      │                   │
│  │  │  └────────────┘ │ │                      ▼                   │
│  │  └─────────────────┘ │          ┌──────────────────────────────┐ │
│  │                      │          │                              │ │
│  │  ┌─────────────────┐ │          │    📡 VPN SENTINEL SERVER    │ │
│  │  │ 🌐 SERVER       │◄┼──────────┤    (Real IP - Port 5000)     │ │
│  │  │ • Port 5000     │ │          │                              │ │
│  │  │ • Telegram Bot  │ │          │  📱 Telegram Notifications   │ │
│  │  │ • REST API      │ │          │  📊 Status Monitoring        │ │
│  │  └─────────────────┘ │          │  🔒 Rate Limiting/Auth      │ │
│  │                      │          └──────────────────────────────┘ │
│  └──────────────────────┘                                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

🔑 Key Points:
• CLIENT runs inside VPN network (shares VPN IP address)
• SERVER runs on host network (uses real IP address)  
• CLIENT → SERVER communication happens over INTERNET via VPN tunnel
• SERVER port 5000 must be accessible from internet
• NO direct Docker network communication between client/server
• This architecture works with ANY VPN provider/client
```

### 🔧 **How It Works**

1. **🔍 Inside Monitoring**: VPN Sentinel Client runs inside your VPN container's network, sharing the same IP and routing
2. **📡 Status Reporting**: Every 5 minutes, client gathers IP info, location data, and performs DNS leak tests
3. **🌐 Internet Communication**: Client connects to server **over internet via VPN tunnel** (not internal Docker network)
4. **📨 Report Transmission**: Client sends HTTP POST requests to server's public port (5000) through VPN connection
5. **📱 Instant Alerts**: Server receives reports and sends Telegram notifications for connections, failures, IP changes, DNS leaks
6. **🚨 Failure Detection**: If client stops reporting (configurable threshold), server alerts you immediately

> **🔑 Critical Architecture Point**: The client doesn't use Docker's internal networking to reach the server. Instead, it makes HTTP requests over the internet (through the VPN tunnel) to the server's public IP and port. This is why port 5000 must be accessible and why the system works with any VPN configuration.

### 🔒 **DNS Leak Detection Logic**

```bash
# What VPN Sentinel Client does every 5 minutes:
1. curl https://ipinfo.io/json          # Get VPN exit location
2. curl https://1.1.1.1/cdn-cgi/trace   # Get DNS resolver location
3. Compare VPN country vs DNS country    # Detect leaks
4. Report all data to server            # Send encrypted status
```

**✅ Secure**: VPN country = DNS country  
**⚠️ Leak Detected**: VPN country ≠ DNS country

## 🐛 **Troubleshooting**

### 🔍 **Common Issues & Solutions**

#### ❌ **Telegram notifications not working**
```bash
# Check bot token and chat ID
docker logs keepalive-server | grep -i telegram

# Test bot manually
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d "chat_id=${TELEGRAM_CHAT_ID}" \
  -d "text=Test message from VPN Sentinel"

# Verify environment variables
docker exec keepalive-server env | grep TELEGRAM
```

#### ❌ **Client not connecting to server**
```bash
# Check client logs for connection errors
docker logs vpn-sentinel-client | tail -20

# Test server connectivity from client (through VPN)
docker exec vpn-sentinel-client curl -v http://your-server-ip:5000/health

# Check if server is running and port is open (requires API key)
curl -H "Authorization: Bearer your-api-key-here" http://localhost:5000/health

# Verify port 5000 is accessible from internet
# From another machine: curl http://your-public-ip:5000/health

# Check firewall/router settings
netstat -tlnp | grep 5000  # Verify port is listening
```

#### ❌ **Port 5000 not accessible**
```bash
# Check Docker port mapping
docker compose ps  # Verify port 5000:5000 mapping

# Check firewall (Ubuntu/Debian)
sudo ufw status
sudo ufw allow 5000

# Check iptables
sudo iptables -L -n | grep 5000

# Router/NAT configuration may be needed for external access
# Forward port 5000 to your server in router settings
```

#### ❌ **VPN container issues**
```bash
# Check VPN container status
docker logs gluetun --tail 20

# Verify VPN IP
docker exec gluetun curl -s https://ipinfo.io/ip

# Test DNS resolution
docker exec gluetun nslookup google.com
```

#### ❌ **DNS leak false positives**
```bash
# Some VPN providers use different countries for DNS
# Check if this is expected behavior from your provider
# You can modify the DNS leak detection logic in keepalive-client.sh

# Temporary disable DNS leak alerts (edit keepalive-client.sh)
# Comment out DNS leak comparison section if needed
```

#### 🏠 **Synology NAS Specific Issues**
```bash
# Synology DSM Docker networking can be tricky, but VPN Sentinel works!

# 1. Use Container Manager (not legacy Docker app)
# Make sure you're using the new Container Manager, not the old Docker package

# 2. Port mapping verification on Synology
# Check DSM Control Panel > Network > Network Interface
# Ensure port 5000 is not blocked by Synology firewall

# 3. Synology firewall configuration
# DSM Control Panel > Security > Firewall > Edit Rules
# Add rule: Allow port 5000 for VPN Sentinel Server

# 4. Check Synology's Docker subnet
# Synology uses different Docker subnets, but this doesn't affect VPN Sentinel
# because we use internet-based communication

# 5. Container Manager project deployment
# Use "docker-compose up" via SSH or Container Manager's Project feature
# Both methods work with VPN Sentinel

# 6. Volume permissions (common Synology issue)
sudo chown -R 1000:1000 /volume1/docker/vpn-sentinel
chmod 755 /volume1/docker/vpn-sentinel
```

### 🔧 **Advanced Debugging**

#### 📝 **Enable Detailed Logging**
```bash
# Add debug environment variable
docker compose down
# Add to .env file:
# DEBUG=true

docker compose up -d

# Watch detailed logs
docker compose logs -f keepalive-server | grep -E "(DEBUG|ERROR|WARNING)"
```

#### 🧪 **Test DNS Leak Detection**
```yaml
# In compose.yaml, temporarily add DNS servers to client:
keepalive-client:
  # ... existing config ...
  dns:
    - 8.8.8.8          # Google DNS (US) - will cause leak alert
    - 8.8.4.4          # Google DNS (US)
```

#### 🔄 **Manual Testing**
```bash
# Send fake heartbeat to test notifications (requires API key)
curl -X POST http://localhost:5000/fake-heartbeat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key-here" \
  -d '{
    "client_id": "test-client",
    "public_ip": "1.2.3.4", 
    "country": "Spain",
    "city": "Madrid",
    "dns_location": "US"
  }'

# This should trigger a DNS leak notification
```

## 🚀 **Production Deployment**

### 🔒 **Security Hardening**
```bash
# 🔐 REQUIRED: Set strong API key (server won't start without it)
KEEPALIVE_API_KEY=$(openssl rand -hex 32)

# 🔒 ALL endpoints now require API key authentication:
# - /health, /status, /keepalive, /fake-heartbeat
# - Server returns no response without valid API key
# - Helps hide server existence from unauthorized access

# Enable IP whitelisting for additional security
ALLOWED_IPS="192.168.1.0/24,10.0.0.0/8"  

# Reduce rate limits for production
MAX_REQUESTS_PER_MINUTE=10
```

### 📊 **Monitoring Integration**
```bash
# Add to your monitoring stack (all endpoints require API key authentication)
# Prometheus endpoint (future feature)
curl -H "Authorization: Bearer your-api-key-here" http://localhost:5000/metrics

# Health check for uptime monitoring
curl -H "Authorization: Bearer your-api-key-here" http://localhost:5000/health

# JSON status for dashboards
curl -H "Authorization: Bearer your-api-key-here" http://localhost:5000/status
```

### 🔄 **Backup Configuration**
```bash
# Backup your configuration
cp .env .env.backup
docker compose config > docker-compose.backup.yaml

# Version control (recommended)
git init
echo ".env" >> .gitignore  # Don't commit secrets
git add docker-compose.yaml keepalive-*
git commit -m "Initial VPN Sentinel setup"
```

### 🏠 **Synology NAS Deployment**
```bash
# VPN Sentinel works great on Synology! Here's the proven setup:

# 1. SSH into your Synology NAS
ssh admin@your-synology-ip

# 2. Create project directory
sudo mkdir -p /volume1/docker/vpn-sentinel
cd /volume1/docker/vpn-sentinel

# 3. Upload project files (via File Station or SCP)
# Copy: docker-compose.yaml, .env, keepalive-client/, keepalive-server/

# 4. Deploy via Container Manager Project (recommended)
# - Open Container Manager in DSM
# - Create new Project
# - Upload docker-compose.yaml
# - Configure environment variables
# - Deploy

# 5. Alternative: SSH deployment
sudo docker compose up -d

# 6. Verify Synology firewall allows port 5000
# DSM > Control Panel > Security > Firewall

# Why VPN Sentinel works well on Synology:
# ✅ Uses internet communication (bypasses Synology networking quirks)
# ✅ No complex internal Docker networking required
# ✅ Works with Container Manager's project system
# ✅ Tested on DSM 7.x with success
```

## 🌍 **Universal VPN Compatibility**

VPN Sentinel works with **any Docker VPN container**. Below are configuration examples for popular VPN clients. **Gluetun is just our example** - you can use any VPN solution you prefer!

### 🔹 **Gluetun (Example - 70+ providers)**
```yaml
vpn-client:  # Generic container name - works with VPN Sentinel
  image: qmcgaw/gluetun
  container_name: vpn-client
  environment:
    - VPN_SERVICE_PROVIDER=${VPN_SERVICE_PROVIDER}
    - OPENVPN_USER=${VPN_USER}
    - OPENVPN_PASSWORD=${VPN_PASSWORD}
```

### 🔹 **OpenVPN**
```yaml
vpn-client:  # Generic container name - works with VPN Sentinel
  image: dperson/openvpn-client
  container_name: vpn-client
  volumes:
    - ./vpn-config.ovpn:/vpn/config.ovpn
```

### 🔹 **WireGuard**
```yaml
vpn-client:  # Generic container name - works with VPN Sentinel
  image: linuxserver/wireguard
  container_name: vpn-client
  environment:
    - PEERS=1
  volumes:
    - ./wireguard:/config
```

### 🔹 **Transmission with VPN**
```yaml
vpn-client:  # Generic container name - works with VPN Sentinel
  image: haugene/transmission-openvpn
  container_name: vpn-client
  environment:
    - OPENVPN_PROVIDER=NORDVPN
    - OPENVPN_USERNAME=${VPN_USER}
    - OPENVPN_PASSWORD=${VPN_PASSWORD}
```

**Just use the generic `network_mode: service:vpn-client` - works with any VPN container!**

## � **VPN Client Comparison**

VPN Sentinel is **VPN client agnostic** - it works with any Docker VPN solution. Here are 5 popular Docker VPN clients you can use:

| VPN Client | Description | Providers Supported | Key Features | Project Link |
|------------|-------------|---------------------|--------------|--------------|
| **🌟 Gluetun** | Lightweight VPN client with extensive provider support | **70+ providers** (NordVPN, Surfshark, ExpressVPN, etc.) | Multi-provider support, automatic updates, kill switch, port forwarding | [qdm12/gluetun](https://github.com/qdm12/gluetun) |
| **🔒 OpenVPN Client** | Generic OpenVPN client for custom configurations | **Any OpenVPN provider** | Custom .ovpn files, flexible configuration, lightweight | [dperson/openvpn-client](https://github.com/dperson/openvpn-client) |
| **⚡ WireGuard** | Modern, fast VPN protocol implementation | **Any WireGuard provider** | High performance, modern cryptography, low latency | [linuxserver/wireguard](https://github.com/linuxserver/docker-wireguard) |
| **📥 Transmission VPN** | BitTorrent client with integrated VPN | **60+ providers** (NordVPN, PIA, etc.) | Built-in torrent client, automatic VPN, web interface | [haugene/transmission-openvpn](https://github.com/haugene/docker-transmission-openvpn) |
| **🌐 PIA WireGuard** | Private Internet Access WireGuard client | **PIA only** | PIA-specific optimization, WireGuard protocol, port forwarding | [thrnz/docker-wireguard-pia](https://github.com/thrnz/docker-wireguard-pia) |

### 🎯 **Why Gluetun is Our Example**

**Gluetun** is a **lightweight VPN client** that connects to multiple VPN service providers. We chose it as our example because:

- ✅ **Lightweight & Fast**: Minimal resource usage, optimized for containers
- ✅ **Multi-Provider Support**: Works with 70+ VPN providers (NordVPN, Surfshark, ExpressVPN, PrivateVPN, etc.)
- ✅ **Simple Configuration**: Just set environment variables - no complex config files
- ✅ **Actively Maintained**: Regular updates with excellent documentation
- ✅ **Feature Complete**: Built-in kill switch, port forwarding, health checks
- ✅ **Community Proven**: Widely used and battle-tested in production

> **📝 What is Gluetun?** Gluetun is a **lightweight VPN client in a thin Docker container**. It connects to your VPN provider using OpenVPN or Wireguard and provides a secure tunnel for other containers. Think of it as a "VPN gateway" that other containers can route through.

**Remember**: Gluetun is just our example. VPN Sentinel's monitoring works with **any Docker VPN client** you choose!

### 🔄 **Switching VPN Clients**

VPN Sentinel uses a **generic "vpn-client" container name**, making it easy to switch VPN solutions:

1. **Replace the VPN service** in `docker-compose.yaml` 
2. **Keep the container name as "vpn-client"** - no network_mode changes needed!
3. **Adjust environment variables** in `.env` to match your VPN client's requirements
4. **VPN Sentinel components work unchanged** - they always connect to "vpn-client"

**Example with WireGuard:**
```yaml
# Replace the vpn-client service with WireGuard:
vpn-client:  # Keep this generic name - VPN Sentinel connects to this
  image: linuxserver/wireguard
  container_name: vpn-client  # Generic name - no changes needed elsewhere
  # ... your WireGuard config ...

# VPN Sentinel client automatically works - no changes needed:
vpn-sentinel-client:
  # ... other config ...
  network_mode: service:vpn-client  # Generic name - always works!
```

**🎯 Benefits of Generic Naming:**
- ✅ **No Configuration Changes**: VPN Sentinel always connects to "vpn-client"
- ✅ **Easy VPN Switching**: Just replace the service definition  
- ✅ **Universal Compatibility**: Works with any Docker VPN container
- ✅ **Simplified Setup**: No need to update multiple references

## ⚠️ **Current Limitations**

### 🚧 **Single Client Architecture**
VPN Sentinel currently operates in a **one-to-one relationship** between client and server:

- **Current Setup**: One VPN Sentinel client → One VPN Sentinel server
- **Limitation**: Each server instance can only monitor one VPN client at a time
- **Workaround**: Deploy multiple server instances for multiple VPN environments

**Example Current Architecture:**
```
VPN Client A → VPN Sentinel Server A (Port 5000)
VPN Client B → VPN Sentinel Server B (Port 5001)  # Separate instance required
VPN Client C → VPN Sentinel Server C (Port 5002)  # Separate instance required
```

### 📊 **Monitoring Interface**
- **Current**: Telegram bot only for notifications and basic commands
- **Limitation**: No web dashboard or visual monitoring interface
- **Workaround**: Use REST API endpoints for custom integrations

## 🚀 **Roadmap & Future Features**

### 🎯 **Phase 1: Multi-Client Support** *(Planned)*
**Goal**: One server managing multiple VPN clients with centralized monitoring

**Planned Features:**
- **Multi-Client Server**: Single server instance handling multiple VPN clients
- **Client Identification**: Enhanced client ID system for unique identification
- **Centralized Notifications**: Consolidated Telegram alerts for all clients
- **Status Aggregation**: Combined status reporting across all monitored VPNs

**Future Architecture:**
```
VPN Client A ┐
VPN Client B ├─→ VPN Sentinel Server (Port 5000) → Telegram Notifications
VPN Client C ┘                                   → Web Dashboard
                                                  → REST API
```

**Implementation Benefits:**
- ✅ **Simplified Deployment**: One server for multiple VPN environments
- ✅ **Centralized Management**: Monitor all VPNs from single interface  
- ✅ **Reduced Resource Usage**: Single server instance vs multiple instances
- ✅ **Unified Notifications**: All VPN alerts in one Telegram conversation
- ✅ **Scalable Architecture**: Easy to add/remove VPN clients

### 🌐 **Phase 2: Web Dashboard** *(Planned)*
**Goal**: Visual web interface for VPN monitoring and management

**Planned Features:**
- **Real-Time Dashboard**: Live VPN status with visual indicators
- **Historical Data**: Connection history and uptime statistics  
- **Geographic Visualization**: World map showing VPN server locations
- **DNS Leak Timeline**: Historical DNS leak detection results
- **Client Management**: Add/remove/configure VPN clients via web UI
- **Alert Configuration**: Customize notification rules and thresholds

**Dashboard Components:**
```
┌─────────────────────────────────────────────────────────────┐
│ VPN Sentinel Dashboard                                      │
├─────────────────────────────────────────────────────────────┤
│ 🟢 Home VPN        │ 🟡 Office VPN      │ 🔴 Mobile VPN    │
│ Netherlands        │ Switzerland        │ Disconnected     │
│ 89.40.181.202     │ 185.234.218.45     │ Last: 2h ago    │
│ Uptime: 99.8%     │ Uptime: 97.2%      │ ⚠️ DNS Leak      │
├─────────────────────────────────────────────────────────────┤
│ 🗺️  Geographic View  │  📊 Statistics  │  ⚙️ Settings     │
└─────────────────────────────────────────────────────────────┘
```

### 🔧 **Phase 3: Advanced Features** *(Future)*
- **Performance Metrics**: Bandwidth, latency, connection speed monitoring
- **Alerting Rules**: Custom alert conditions and notification channels
- **API Extensions**: Webhooks, Slack integration, email notifications
- **Mobile App**: Dedicated mobile application for VPN monitoring
- **Load Balancing**: Intelligent VPN server selection and failover

## 💡 **Contributing to Development**

Want to help implement these features? We welcome contributions:

### 🎯 **High Priority Items:**
1. **Multi-Client Server Logic**: Modify server to handle multiple client connections
2. **Database Integration**: Add SQLite/PostgreSQL for client state management  
3. **Web Dashboard Frontend**: React/Vue.js dashboard with real-time updates
4. **Enhanced API**: Extended REST endpoints for multi-client operations

### 🛠️ **Development Areas:**
- **Backend**: Python Flask server enhancements for multi-client support
- **Frontend**: Web dashboard UI/UX design and implementation
- **DevOps**: Docker orchestration for scalable multi-client deployments  
- **Documentation**: Updated guides and API documentation

### � **Contribution Guidelines:**
```bash
# 1. Fork the repository
git clone https://github.com/your-username/vpn-sentinel.git

# 2. Create feature branch
git checkout -b feature/multi-client-support

# 3. Implement changes
# Focus on backward compatibility with current single-client setup

# 4. Test thoroughly
docker compose up -d  # Ensure existing functionality works

# 5. Submit pull request with detailed description
```

## �📚 **Additional Resources**

### 📖 **Documentation**
- **[Gluetun VPN Provider Setup](https://github.com/qdm12/gluetun/wiki)** - Configure 25+ VPN providers
- **[Telegram Bot API](https://core.telegram.org/bots/api)** - Official Telegram Bot documentation
- **[Docker Compose Networking](https://docs.docker.com/compose/networking/)** - Understanding container networks
- **[VPN Provider Comparison](https://www.privacyguides.org/vpn/)** - Choose the right VPN service

### 🛠️ **Advanced Topics**
- **DNS Leak Testing**: Understanding how DNS leaks expose your location
- **VPN Kill Switches**: Why software kill switches aren't enough
- **Network Isolation**: Docker networking security best practices
- **Monitoring at Scale**: Deploying VPN Sentinel across multiple servers

## ⚠️ **Important Notices**

### 🎓 **Educational Purpose**
This project is designed for **educational and privacy protection purposes**. Please ensure you:

- ✅ Comply with local laws regarding VPN usage
- ✅ Respect terms of service for all online services
- ✅ Use VPNs for legitimate privacy protection
- ✅ Support content creators and legal platforms

### 🔒 **Privacy & Security**
- **No Data Collection**: VPN Sentinel doesn't store or transmit your personal data
- **Local Processing**: All monitoring happens on your own infrastructure  
- **Open Source**: Full transparency - review the code yourself
- **Telegram Security**: Bot messages are encrypted by Telegram's infrastructure

### 🤝 **Community & Support**
This is an open-source project maintained by the community. We welcome:

- 🐛 **Bug Reports**: Help us improve by reporting issues
- 💡 **Feature Requests**: Suggest new monitoring capabilities  
- 📖 **Documentation**: Improve guides and tutorials
- 🔧 **Code Contributions**: Submit pull requests for enhancements

## 📝 **License & Contributing**

This project is licensed under the [MIT License](LICENSE) - feel free to use, modify, and distribute.

**Contributing Guidelines:**
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

### 🔗 **Quick Links**
[🚀 Quick Start](#-quick-start) | [🔧 Configuration](#-advanced-configuration) | [🐛 Troubleshooting](#-troubleshooting) | [📊 API Docs](#-monitoring-dashboard) | [🤝 Contributing](#-license--contributing)

**Made with ❤️ for VPN privacy and security**