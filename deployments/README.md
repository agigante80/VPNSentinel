# VPN Sentinel - Deployment Options

VPN Sentinel offers **four flexible deployment scenarios** to fit different use cases, from simple single-server setups to distributed monitoring across multiple locations.

## 🎯 Deployment Scenarios

### 📦 [All-in-One Deployment](./all-in-one/) - **Recommended for Most Users**

**What**: Both client and server in a single Docker Compose stack  
**Best for**: Single-location monitoring, testing, simple setups

```
┌─────────────────────────────────────┐
│           Docker Host               │
│  ┌─────────────┐  ┌─────────────┐   │
│  │ VPN Client  │  │ VPN Server  │   │
│  │   +         │  │    +        │   │
│  │ Sentinel    │──│ Telegram    │   │
│  │ Client      │  │ Bot         │   │
│  └─────────────┘  └─────────────┘   │
└─────────────────────────────────────┘
```

✅ **Advantages:**
- Simplest setup - everything in one place
- Perfect for home users and small setups
- All components managed together
- Ideal for learning and testing

❌ **Limitations:**  
- Single point of failure
- Cannot monitor multiple locations
- Server and client share the same host

---

### 🌐 [Client with VPN Deployment](./client-with-vpn/) - **For Remote VPN Monitoring**

**What**: VPN client + monitoring client that reports to a remote server  
**Best for**: Distributed monitoring of VPN-protected services, multiple locations, edge devices

```
┌─────────────────┐    Internet    ┌──────────────────┐
│   Location A    │                │   Remote Server  │
│ ┌─────────────┐ │    ────────    │ ┌─────────────┐  │
│ │ VPN Client  │ │                │ │ VPN Server  │  │
│ │   +         │ │       API      │ │    +        │  │
│ │ Sentinel    │─┼─────────────────┼─│ Telegram    │  │
│ │ Client      │ │    Reports     │ │ Bot         │  │
│ └─────────────┘ │                │ └─────────────┘  │
└─────────────────┘                └──────────────────┘
```

✅ **Advantages:**
- Monitor VPN connections at multiple locations from one server
- Lightweight deployment on each site
- Centralized monitoring and alerts
- Scales to hundreds of clients

❌ **Requirements:**
- Needs a remote VPN Sentinel Server
- Requires network connectivity to server
- More complex initial setup

---

### 📡 [Client Standalone Deployment](./client-standalone/) - **For Remote Service Monitoring**

**What**: Only the monitoring client that reports to a remote server (no VPN)  
**Best for**: Monitoring non-VPN services, distributed monitoring without VPN requirements

```
┌─────────────────┐    Internet    ┌──────────────────┐
│   Location A    │                │   Remote Server  │
│ ┌─────────────┐ │    ────────    │ ┌─────────────┐  │
│ │   Service   │ │       API      │ │ VPN Server  │  │
│ │   +         │ │    Reports     │ │    +        │  │
│ │ Sentinel    │─┼─────────────────┼─│ Telegram    │  │
│ │ Client      │ │                │ │ Bot         │  │
│ └─────────────┘ │                │ └─────────────┘  │
└─────────────────┘                └──────────────────┘
```

✅ **Advantages:**
- Monitor any service connectivity at remote sites
- No VPN configuration required
- Lightweight and simple deployment
- Centralized monitoring and alerts

❌ **Requirements:**
- Needs a remote VPN Sentinel Server
- Service must be accessible for monitoring
- Requires network connectivity to server

---

### 🏢 [Server Central Deployment](./server-central/) - **For Centralized Control**

**What**: Only the monitoring server that receives reports from remote clients  
**Best for**: Central monitoring hubs, team environments, cloud hosting

```
┌──────────────────────┐           ┌─────────────────┐
│    VPS/Cloud Host    │           │   Location A    │
│  ┌─────────────┐     │           │ ┌─────────────┐ │
│  │ VPN Server  │◄────┼───────────┼─│   Client    │ │
│  │    +        │     │  Reports  │ │     #1      │ │
│  │ Telegram    │     │           │ └─────────────┘ │
│  │ Bot         │     │           └─────────────────┘
│  │    +        │◄────┤           ┌─────────────────┐
│  │ REST API    │     │           │   Location B    │
│  └─────────────┘     │           │ ┌─────────────┐ │
└──────────────────────┘           │ │   Client    │ │
                                   │ │     #2      │ │
                                   │ └─────────────┘ │
                                   └─────────────────┘
```

✅ **Advantages:**
- Centralized monitoring dashboard
- Supports unlimited remote clients  
- Perfect for cloud hosting
- Team-friendly with shared notifications

❌ **Requirements:**
- Needs publicly accessible server
- Clients must be deployed separately
- Requires proper security configuration

## 🚀 Quick Start Guide

### 1. Choose Your Deployment

| Scenario | Use When | Complexity |
|----------|----------|------------|
| **[All-in-One](./all-in-one/)** | Testing, home use, single location | 🟢 Simple |
| **[Client with VPN](./client-with-vpn/)** | You have a remote server, monitoring VPN sites | 🟡 Medium |
| **[Client Standalone](./client-standalone/)** | You have a remote server, monitoring any services | 🟡 Medium |
| **[Server Central](./server-central/)** | Creating central monitoring hub | 🟡 Medium |

### 2. Follow Deployment Instructions

Each deployment has its own folder with:
- `compose.yaml` - Docker Compose configuration
- `.env.example` - Environment template  
- `README.md` - Detailed setup instructions

### 3. Basic Setup Steps

```bash
# Navigate to your chosen deployment
cd deployments/all-in-one/        # OR client-with-vpn/ OR client-standalone/ OR server-central/

# Copy and configure environment
cp .env.example .env
nano .env                      # Edit your settings

# Start services  
docker-compose up -d

# Check logs
docker-compose logs -f
```

## 🔧 Common Configuration

All deployments share these core configuration patterns:

### Essential Settings
```bash
# VPN Provider (for client deployments)
VPN_SERVICE_PROVIDER=your_provider
VPN_USER=your_username
VPN_PASSWORD=your_password

# VPN Sentinel Authentication  
VPN_SENTINEL_API_KEY=your_secure_api_key

# Telegram Notifications
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Secrets from files (Docker/Compose secrets)

Keep the API key out of the container environment by mounting it as a secret file. Set the plain variable
empty (the root `compose.yaml` injects `VPN_SENTINEL_API_KEY=` anyway) because setting both forms is a fatal error:

```yaml
services:
  vpn-sentinel-server:
    secrets:
      - vpn_sentinel_api_key
    environment:
      - VPN_SENTINEL_API_KEY=
      - VPN_SENTINEL_API_KEY_FILE=/run/secrets/vpn_sentinel_api_key

secrets:
  vpn_sentinel_api_key:
    file: ./secrets/vpn_sentinel_api_key
```

`TELEGRAM_BOT_TOKEN_FILE` and `TELEGRAM_CHAT_ID_FILE` work the same way. An unreadable or empty file stops the
process instead of disabling authentication.

### Security Best Practices
```bash
# Use strong API keys (64+ characters)
VPN_SENTINEL_API_KEY=$(openssl rand -hex 32)

# Configure IP restrictions (production)
VPN_SENTINEL_SERVER_ALLOWED_IPS=203.0.113.10,203.0.113.11

# Use proper firewall rules
sudo ufw allow 5000/tcp  # Server port
```

## 📊 Deployment Comparison

| Feature | Unified | Client-Only | Server-Only |
|---------|---------|-------------|-------------|
| **Setup Complexity** | 🟢 Simple | 🟡 Medium | 🟡 Medium |
| **Resource Usage** | 🟡 Medium | 🟢 Low | 🟡 Medium |
| **Scalability** | ❌ Limited | ✅ High | ✅ High |
| **Multi-Location** | ❌ No | ✅ Yes | ✅ Yes |
| **Single Point Failure** | ❌ Yes | ✅ Resilient | 🟡 Server Only |
| **Best For** | Home/Test | Edge Monitoring | Central Hub |

## 🛠️ Advanced Scenarios

### Hybrid Deployments

**Scenario**: Local unified + remote clients
```
Main Location: Unified Deployment (server + local client)
Remote Sites: Client-Only Deployments → Report to main server
```

**Scenario**: Multiple servers with geo-redundancy
```  
Region A: Server-Only + Local Clients
Region B: Server-Only + Local Clients  
Cross-region: Clients can failover between servers
```

### Production Considerations

1. **Load Balancing**: Use nginx/HAProxy for server-only deployments
2. **SSL Termination**: Deploy behind reverse proxy with SSL
3. **Monitoring**: Add Prometheus/Grafana for metrics
4. **Backup**: Regular backups of server configuration and data
5. **Updates**: Rolling updates for zero-downtime deployments

## 🧱 Unraid

Install from the Unraid Apps tab (Community Applications) once the repository is listed, or add the
template URLs by hand under Docker, Add Container, Template:

- Server: `https://raw.githubusercontent.com/agigante80/VPNSentinel/main/unraid/vpn-sentinel-server.xml`
- Client: `https://raw.githubusercontent.com/agigante80/VPNSentinel/main/unraid/vpn-sentinel-client.xml`

1. **Server.** Set an API key (required: an empty key runs the server with authentication disabled) and
   optionally the Telegram token and chat ID. The WebUI link opens `/dashboard`.
2. **Client.** In Extra Parameters change `--network=container:gluetun` to the exact name of your VPN
   container. Set `VPN_SENTINEL_URL` to `http://HOST:PORT`, where HOST is the Unraid host and PORT the
   server's mapped API port (default 5000). Use the same API key and API path as the server.
3. **Firewall.** Add the LAN subnet of HOST to the VPN container's `FIREWALL_OUTBOUND_SUBNETS`. Without
   it the keepalive is blocked, the client logs `Failed to send keepalive to <server_url>` and never
   appears on the dashboard.

Recreating the VPN container breaks the client until the client is recreated too. The templates live in
`unraid/` and are checked by `tests/unit/test_unraid_templates.py`.

## 📁 Directory Structure

```
deployments/
├── README.md                 # This overview (you are here)
│
├── all-in-one/                  # Complete solution (server + client)
│   ├── compose.yaml
│   ├── .env.example
│   └── README.md
│
├── client-with-vpn/              # Remote monitoring client with VPN
│   ├── compose.yaml
│   ├── .env.example  
│   └── README.md
│
├── client-standalone/              # Remote monitoring client (no VPN)
│   ├── compose.yaml
│   ├── .env.example  
│   └── README.md
│
└── server-central/              # Central monitoring server
    ├── compose.yaml
    ├── .env.example
    └── README.md
```

## 🆘 Need Help?

- **Setup Issues**: Check the README.md in your chosen deployment folder
- **Configuration**: See `.env.example` files for all available options
- **Troubleshooting**: Each deployment README has a troubleshooting section
- **Support**: Create an issue in the main repository

## 🔗 Quick Links

- **[Main Project README](../README.md)** - Project overview and features
- **[Component Documentation](../docs/)** - Detailed technical docs
- **[Architecture](../docs/ARCHITECTURE.md)** - Deployment patterns and configuration reference

---

**Ready to deploy?** Choose your scenario above and follow the specific deployment guide! 🚀