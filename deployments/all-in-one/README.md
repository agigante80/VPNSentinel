# VPN Sentinel - Unified Deployment

This deployment includes both the VPN Sentinel Client and Server in a single Docker Compose stack. This is the **simplest deployment option** and is recommended for most users.

## 🎯 What's Included

- **VPN Client Container** (Gluetun example - replace with your preferred VPN solution)
- **VPN Sentinel Client** (monitors from inside VPN network)
- **VPN Sentinel Server** (receives reports and sends Telegram notifications)
- **Dual-network architecture** for reliable monitoring

## 🚀 Quick Start

1. **Copy and configure environment file:**
   ```bash
   cp .env.example .env
   nano .env  # Configure your settings
   ```

2. **Start the services:**
   ```bash
   docker-compose up -d
   ```

3. **Check logs:**
   ```bash
   docker-compose logs -f
   ```

## ⚙️ Configuration

### Required Settings

Edit `.env` and configure these essential settings:

```bash
# VPN Provider Settings (replace with your VPN)
VPN_SERVICE_PROVIDER=your_provider
VPN_USER=your_username
VPN_PASSWORD=your_password

# VPN Sentinel Security
VPN_SENTINEL_API_KEY=your_secure_api_key_here

# Server Configuration  
VPN_SENTINEL_SERVER_PORT=5000

# Telegram Notifications (highly recommended)
TELEGRAM_BOT_TOKEN=your_bot_token
VPN_SENTINEL_TELEGRAM_CHAT_ID=your_chat_id
```

### Optional Settings

```bash
# Monitoring Intervals
VPN_SENTINEL_ALERT_THRESHOLD_MINUTES=15
VPN_SENTINEL_CHECK_INTERVAL_MINUTES=5

# Network Security
VPN_SENTINEL_ALLOWED_IPS=192.168.1.0/24,10.0.0.0/8

# Timezone
TZ=Europe/Madrid
```

## 🔄 Replacing the VPN Client

The example uses **Gluetun**, but you can replace it with any VPN client:

### Popular VPN Clients:
- **Gluetun**: `qmcgaw/gluetun` (70+ providers)
- **OpenVPN**: `dperson/openvpn-client`
- **WireGuard**: `linuxserver/wireguard`
- **NordVPN**: `ghcr.io/bubuntux/nordvpn`
- **Surfshark**: Custom configs

### How to Replace:
1. Update the `vpn-client` service in `compose.yaml`
2. Ensure the container name stays `vpn-client`
3. Configure your VPN credentials in `.env`

## 📊 Monitoring

### Health Checks
Both containers include comprehensive health monitoring:
- **Client**: VPN connectivity, server communication, process monitoring
- **Server**: HTTP endpoints, process health, API responsiveness

### API Endpoints
- Health: `http://YOUR_SERVER:5000/api/v1/health`
- Status: `http://YOUR_SERVER:5000/api/v1/status` (requires API key)

### Telegram Commands
- `/ping` - Server status and configuration
- `/status` - Detailed client status and monitoring info
- `/help` - Command list and bot information

## 🛠️ Troubleshooting

### Check Container Status
```bash
docker-compose ps
docker-compose logs vpn-client
docker-compose logs vpn-sentinel-client  
docker-compose logs vpn-sentinel-server
```

### Verify VPN Connection
```bash
# Check client's public IP (should be VPN IP)
docker-compose exec vpn-sentinel-client curl -s https://ipinfo.io/ip

# Check server's public IP (should be real IP)  
docker-compose exec vpn-sentinel-server curl -s https://ipinfo.io/ip
```

### Test API Communication
```bash
# Health check (no authentication)
curl http://localhost:5000/api/v1/health

# Authenticated test
curl -X GET -H "X-API-Key: YOUR_API_KEY" http://localhost:5000/api/v1/status
```

## 🔧 Advanced Configuration

### Custom Network Settings
The compose file uses dual networks:
- `vpn-client-network`: VPN-isolated network for monitoring
- `vpn-sentinel-server`: Direct network for server communications

### Volume Mounts
- Server logs and data persist in Docker volumes
- Client script is mounted from the build context

### Resource Limits
Containers are configured with reasonable resource limits:
- Memory: 256MB per container
- CPU: 0.5 cores per container

## 📁 File Structure

```
all-in-one/
├── compose.yaml          # Docker Compose configuration
├── .env.example          # Environment template
├── .env                  # Your configuration (create from example)
└── README.md            # This file
```

## 🔗 External Resources

- **Main Project**: [VPN Sentinel Repository](../)
- **Client with VPN Deployment**: [../client-with-vpn/](../client-with-vpn/)
- **Client Standalone Deployment**: [../client-standalone/](../client-standalone/)
- **Server Central Deployment**: [../server-central/](../server-central/)
- **Documentation**: [../../wiki-content/](../../wiki-content/)

---

**Need help?** Check the main project README or create an issue on GitHub.