# VPN Sentinel - Client-Only Deployment

This deployment contains **only the VPN Sentinel Client** that monitors VPN connections and reports to a **remote VPN Sentinel Server**. Perfect for distributed monitoring setups where you want to monitor VPNs across multiple locations.

## 🎯 What's Included

- **VPN Client Container** (Gluetun example - replace with your preferred VPN solution)
- **VPN Sentinel Client** (monitors from inside VPN network and reports to remote server)

## ❗ Prerequisites

**You need a running VPN Sentinel Server** accessible from this client. Options:

1. **Deploy server separately** using [../server-only/](../server-only/)
2. **Use existing unified deployment** from [../unified/](../unified/)
3. **Use a remote hosted server** (cloud/VPS instance)

## 🚀 Quick Start

1. **Copy and configure environment file:**
   ```bash
   cp .env.example .env
   nano .env  # Configure your settings
   ```

2. **Configure remote server connection:**
   ```bash
   # Edit .env and set these REQUIRED values:
   VPN_SENTINEL_SERVER_API_BASE_URL=https://your-server.example.com:5000
   VPN_SENTINEL_API_KEY=your_secure_api_key_here
   ```

3. **Start the client:**
   ```bash
   docker-compose up -d
   ```

4. **Check logs:**
   ```bash
   docker-compose logs -f
   ```

## ⚙️ Configuration

### Required Settings

Edit `.env` and configure these **essential** settings:

```bash
# Remote Server Connection (REQUIRED)
VPN_SENTINEL_SERVER_API_BASE_URL=https://your-server.example.com:5000
VPN_SENTINEL_API_KEY=your_secure_api_key_here

# VPN Provider Settings (REQUIRED)
VPN_SERVICE_PROVIDER=your_provider
VPN_USER=your_username
VPN_PASSWORD=your_password

# Client Identity
VPN_SENTINEL_CLIENT_ID=vpn-monitor-client-01
```

### Optional Settings

```bash
# Monitoring Behavior
VPN_SENTINEL_CHECK_INTERVAL=300  # 5 minutes

# Timezone
TZ=Europe/Madrid
```

## 🔄 Replacing the VPN Client

The example uses **Gluetun**, but you can replace it with any VPN client. See [Popular VPN Clients section in unified deployment](../unified/README.md#replacing-the-vpn-client) for options.

## 📊 Monitoring

### Health Checks
- **VPN Client**: Connectivity and IP verification
- **Sentinel Client**: Process monitoring, VPN status, remote server communication

### Remote Monitoring
All monitoring data is sent to your remote VPN Sentinel Server:
- VPN connection status and public IP
- DNS leak test results  
- Geographic location information
- Provider and network details

### Telegram Notifications
Notifications are handled by the **remote server**, not this client. Configure Telegram on your server deployment.

## 🛠️ Troubleshooting

### Check Container Status
```bash
docker-compose ps
docker-compose logs vpn-client
docker-compose logs vpn-sentinel-client
```

### Verify VPN Connection
```bash
# Check client's public IP (should be VPN IP)
docker-compose exec vpn-sentinel-client curl -s https://ipinfo.io/ip

# Should be different from your real IP
curl -s https://ipinfo.io/ip
```

### Test Remote Server Communication
```bash
# Test health endpoint (no auth required)
curl -s https://your-server.example.com:5000/api/v1/health

# Test with authentication
curl -X GET -H "X-API-Key: YOUR_API_KEY" https://your-server.example.com:5000/api/v1/status
```

### Common Issues

#### "Connection refused" to remote server
- Verify `VPN_SENTINEL_SERVER_API_BASE_URL` is correct
- Check server is running and accessible
- Verify network/firewall allows outbound connections

#### "Authentication failed" errors  
- Verify `VPN_SENTINEL_API_KEY` matches server configuration
- Check API key has no extra spaces or characters

#### Client not appearing in server logs
- Check client container logs for connection errors
- Verify VPN is working (client should have different IP)
- Confirm server API path is correct (`/api/v1` by default)

## 🔧 Advanced Configuration

### Multiple Clients
Deploy multiple client instances with different `VPN_SENTINEL_CLIENT_ID` values:

```bash
# Client 1
VPN_SENTINEL_CLIENT_ID=vpn-monitor-location-1

# Client 2  
VPN_SENTINEL_CLIENT_ID=vpn-monitor-location-2
```

### Custom Check Intervals
Adjust monitoring frequency:
```bash
VPN_SENTINEL_CHECK_INTERVAL=180  # 3 minutes (more frequent)
VPN_SENTINEL_CHECK_INTERVAL=600  # 10 minutes (less frequent)
```

### Network Configuration
The client uses the VPN network for all monitoring traffic to ensure accurate testing.

## 📁 File Structure

```
client-only/
├── compose.yaml          # Docker Compose configuration (client only)
├── .env.example          # Environment template (client-focused)
├── .env                  # Your configuration (create from example)
└── README.md            # This file
```

## 🔗 Related Deployments

- **Server-Only**: [../server-only/](../server-only/) - Deploy just the server component
- **Unified**: [../unified/](../unified/) - Deploy both client and server together
- **Main Project**: [../../](../../) - Main VPN Sentinel repository

---

**Need a server?** Check out the [server-only deployment](../server-only/) to host your own VPN Sentinel Server.