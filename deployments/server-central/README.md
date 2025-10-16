# VPN Sentinel - Server-Only Deployment

This deployment contains **only the VPN Sentinel Server** that receives monitoring reports from remote VPN Sentinel Clients. Perfect for centralized monitoring setups where you manage VPN connections across multiple locations.

## 🎯 What's Included

- **VPN Sentinel Server** (receives reports, sends Telegram notifications, provides API)
- **REST API endpoints** for client communication and external integration
- **Telegram bot** for interactive monitoring and alerts

## 🌐 Use Cases

This server-only deployment is perfect for:

- **Multi-location monitoring**: Central server receiving reports from multiple remote clients
- **Cloud hosting**: Deploy server on VPS/cloud while clients run on local networks
- **Team monitoring**: Shared server for monitoring team's VPN connections
- **API integration**: Central server for external monitoring systems

## 🚀 Quick Start

1. **Copy and configure environment file:**
   ```bash
   cp .env.example .env
   nano .env  # Configure your settings
   ```

2. **Configure essential settings:**
   ```bash
   # Generate a secure API key
   VPN_SENTINEL_API_KEY=$(openssl rand -hex 32)
   
   # Set up Telegram notifications
   TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
   VPN_SENTINEL_TELEGRAM_CHAT_ID=your_chat_id
   ```

3. **Start the server:**
   ```bash
   docker-compose up -d
   ```

4. **Verify server is running:**
   ```bash
   curl http://localhost:5000/api/v1/health
   ```

## ⚙️ Configuration

### Required Settings

Edit `.env` and configure these **essential** settings:

```bash
# Server Authentication (REQUIRED)
VPN_SENTINEL_API_KEY=your_secure_64_character_api_key_here

# Telegram Notifications (HIGHLY RECOMMENDED)  
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxyz
VPN_SENTINEL_TELEGRAM_CHAT_ID=123456789

# Server Port
VPN_SENTINEL_SERVER_PORT=5000
```

### Optional Settings

```bash
# Monitoring Thresholds
VPN_SENTINEL_ALERT_THRESHOLD_MINUTES=15  # Alert after 15min offline
VPN_SENTINEL_CHECK_INTERVAL_MINUTES=5    # Check clients every 5min

# Security
VPN_SENTINEL_RATE_LIMIT_REQUESTS=30      # 30 requests/minute per IP
VPN_SENTINEL_ALLOWED_IPS=192.168.1.0/24  # IP whitelist (optional)

# Timezone
TZ=Europe/Madrid
```

## 🔐 Security Setup

### 1. Generate Secure API Key
```bash
# Generate a strong API key
openssl rand -hex 32

# Or use this format
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Configure Firewall
```bash
# Allow only necessary ports
sudo ufw allow 5000/tcp    # VPN Sentinel API
sudo ufw enable
```

### 3. Set Up Reverse Proxy (Recommended)
For production use, put the server behind nginx/Apache:

```nginx
# Nginx configuration
server {
    listen 443 ssl;
    server_name vpn-monitor.example.com;
    
    location /api/v1/ {
        proxy_pass http://localhost:5000/api/v1/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📊 Monitoring & API

### Health Check
```bash
# Public health endpoint (no authentication required)
curl http://your-server:5000/api/v1/health
```

### API Endpoints
All endpoints except `/health` require `X-API-Key` header:

```bash
# Server status
curl -H "X-API-Key: YOUR_API_KEY" http://your-server:5000/api/v1/status

# Client keepalive (used by clients)
curl -X POST -H "X-API-Key: YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"client_id":"test","public_ip":"1.2.3.4"}' \
     http://your-server:5000/api/v1/keepalive
```

### Telegram Bot Commands
Once clients connect, use these commands in your Telegram chat:

- `/ping` - Server status and configuration  
- `/status` - Detailed client status report
- `/help` - Command list and information

## 👥 Client Setup

Clients need to be configured to connect to this server. Share these details with your client deployments:

```bash
# Client configuration (.env file)
VPN_SENTINEL_SERVER_API_BASE_URL=https://your-server.example.com:5000
VPN_SENTINEL_API_KEY=your_secure_api_key_here
```

See [client deployments](../client-with-vpn/) and [../client-standalone/] for client setup instructions.

## 🛠️ Troubleshooting

### Check Server Status
```bash
docker-compose ps
docker-compose logs vpn-sentinel-server
```

### Test API Connectivity
```bash
# Health check (should return JSON)
curl -v http://localhost:5000/api/v1/health

# With authentication
curl -v -H "X-API-Key: YOUR_API_KEY" http://localhost:5000/api/v1/status
```

### Common Issues

#### "Port already in use" error
```bash
# Check what's using port 5000
sudo netstat -tlnp | grep :5000

# Change port in .env file
VPN_SENTINEL_SERVER_PORT=5001
```

#### Clients can't connect
- Check firewall allows the server port
- Verify `VPN_SENTINEL_API_KEY` matches on both server and clients
- Test connectivity: `curl http://YOUR_SERVER_IP:5000/api/v1/health`

#### Telegram notifications not working
- Verify `TELEGRAM_BOT_TOKEN` is correct (from @BotFather)
- Check `VPN_SENTINEL_TELEGRAM_CHAT_ID` (from @userinfobot)
- Send `/start` to your bot in Telegram

## 📈 Scaling & Performance

### Resource Requirements
- **Memory**: 256MB minimum, 512MB recommended
- **CPU**: 0.5 cores minimum, 1 core recommended  
- **Storage**: 1GB minimum (for logs and data)
- **Network**: 100Mbps recommended for many clients

### Client Limits
- Default configuration supports **50-100 concurrent clients**
- Increase `VPN_SENTINEL_RATE_LIMIT_REQUESTS` for more clients
- Consider load balancer for 200+ clients

### Database Options
For persistent client data (optional):
```bash
# Add to compose.yaml volumes section
volumes:
  - vpn-sentinel-data:/data
  
# Configure in .env
VPN_SENTINEL_DB_PATH=/data/vpn_sentinel.db
```

## 🔧 Advanced Configuration

### Custom Domain Setup
```bash
# Configure custom domain in .env
VPN_SENTINEL_SERVER_HOSTNAME=vpn-monitor.example.com

# Update client configurations
VPN_SENTINEL_SERVER_API_BASE_URL=https://vpn-monitor.example.com
```

### SSL/TLS Setup
Use reverse proxy (nginx/Apache) or load balancer for SSL termination.

### Monitoring Integration
The server exposes metrics suitable for:
- **Prometheus**: Custom metrics endpoint can be added
- **Grafana**: Dashboard for client statistics
- **Uptime monitoring**: Health endpoint for external monitoring

## 📁 File Structure

```
server-central/
├── compose.yaml          # Docker Compose configuration (server only)
├── .env.example          # Environment template (server-focused)  
├── .env                  # Your configuration (create from example)
└── README.md            # This file
```

## 🔗 Related Deployments

- **Client with VPN**: [../client-with-vpn/](../client-with-vpn/) - Deploy VPN clients to connect to this server
- **Client Standalone**: [../client-standalone/](../client-standalone/) - Deploy standalone clients to connect to this server
- **All-in-One**: [../all-in-one/](../all-in-one/) - Deploy both client and server together  
- **Main Project**: [../../](../../) - Main VPN Sentinel repository

---

**Need clients?** Check out the [client deployments](../client-with-vpn/) and [../client-standalone/] to connect remote clients to this server.