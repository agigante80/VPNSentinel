# VPN Sentinel Environment Variables

This document lists all environment variables used by VPN Sentinel components.

## 🖥️ Server Configuration

### Port Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `VPN_SENTINEL_SERVER_API_PORT` | `5000` | Port for API endpoints (authenticated) |
| `VPN_SENTINEL_SERVER_HEALTH_PORT` | `8081` | Port for health check endpoints (public) |
| `VPN_SENTINEL_SERVER_DASHBOARD_PORT` | `8080` | Port for web dashboard |

### TLS/Security
| Variable | Default | Description |
|----------|---------|-------------|
| `VPN_SENTINEL_TLS_CERT_PATH` | _(empty)_ | Path to TLS certificate file for HTTPS |
| `VPN_SENTINEL_TLS_KEY_PATH` | _(empty)_ | Path to TLS private key file for HTTPS |
| `VPN_SENTINEL_API_KEY` | _(empty)_ | API key for authenticated endpoints |
| `VPN_SENTINEL_ALLOW_INSECURE` | `false` | Allow insecure TLS connections (dev only) |

### API Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `VPN_SENTINEL_API_PATH` | `/api/v1` | Base path for API endpoints |

### Version Information
| Variable | Default | Description |
|----------|---------|-------------|
| `VERSION` | `1.0.0-dev` | Application version string |
| `COMMIT_HASH` | _(auto-detected)_ | Git commit hash for versioning |

## 📱 Client Configuration

### Connection Settings
| Variable | Default | Description |
|----------|---------|-------------|
| `VPN_SENTINEL_URL` | `http://your-server-url:5000` | Base URL of VPN Sentinel server |
| `VPN_SENTINEL_API_PATH` | `/api/v1` | API path (must match server) |
| `VPN_SENTINEL_CLIENT_ID` | _(auto-generated)_ | Unique client identifier (kebab-case) |

### Timing
| Variable | Default | Description |
|----------|---------|-------------|
| `VPN_SENTINEL_TIMEOUT` | `30` | Request timeout in seconds |
| `VPN_SENTINEL_INTERVAL` | `300` | Keepalive interval in seconds (5 minutes) |

### Geolocation
| Variable | Default | Description |
|----------|---------|-------------|
| `VPN_SENTINEL_GEOLOCATION_SERVICE` | `auto` | Geolocation provider: `auto`, `ipinfo.io`, `ip-api.com`, or `ipwhois.app` |

### Debug
| Variable | Default | Description |
|----------|---------|-------------|
| `VPN_SENTINEL_DEBUG` | `false` | Enable debug logging |

## 📬 Telegram Integration

### Bot Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | _(empty)_ | Telegram Bot API token from @BotFather |
| `TELEGRAM_CHAT_ID` | _(empty)_ | Telegram chat ID to send messages to |

### Testing Telegram

You can test Telegram integration by exporting these variables in your console:

```bash
# Set Telegram credentials
export TELEGRAM_BOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
export TELEGRAM_CHAT_ID="-1001234567890"

# Run manual test script
python3 tests/test_telegram_manual.py

# Or start server to test notifications
docker compose up vpn-sentinel-server
```

**Automatic Notifications:**
- 🚀 **Server started** - When server starts up
- ✅ **Client connected** - When a VPN client first connects
- 🔄 **IP changed** - When a client's VPN IP changes
- ⚠️ **No clients** - When no clients are connected

**Bot Commands:**
- `/ping` - Test bot connectivity and get server info
- `/status` - Get detailed status of all VPN clients
- `/help` - Show available commands

**Logging:**
Every Telegram message sent or received is logged with full details:
```
INFO [telegram] 📤 Sending message: 🚀 VPN Keepalive Server Started...
INFO [telegram] ✅ Message sent successfully
INFO [telegram] 📥 Received message (ID 123): /ping
INFO [telegram] 🎯 Processing command: /ping
```

## 🔧 Development Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `production` | Environment name: `production`, `development`, `testing` |
| `FLASK_ENV` | `production` | Flask environment mode |

## 📝 Example Configurations

### Development Client
```bash
export VPN_SENTINEL_URL="http://localhost:5000"
export VPN_SENTINEL_CLIENT_ID="dev-laptop"
export VPN_SENTINEL_INTERVAL="60"  # More frequent checks
export VPN_SENTINEL_DEBUG="true"
export VPN_SENTINEL_GEOLOCATION_SERVICE="ipinfo.io"
```

### Production Server
```bash
export VPN_SENTINEL_SERVER_API_PORT="5000"
export VPN_SENTINEL_SERVER_HEALTH_PORT="8081"
export VPN_SENTINEL_SERVER_DASHBOARD_PORT="8080"
export VPN_SENTINEL_API_KEY="your-secure-api-key-here"
export VPN_SENTINEL_TLS_CERT_PATH="/certs/server.crt"
export VPN_SENTINEL_TLS_KEY_PATH="/certs/server.key"
export VERSION="1.2.3"
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="your-chat-id"
```

### Secure HTTPS Client
```bash
export VPN_SENTINEL_URL="https://vpn-sentinel.example.com:5000"
export VPN_SENTINEL_CLIENT_ID="office-vpn-primary"
export VPN_SENTINEL_API_KEY="matching-server-api-key"
export VPN_SENTINEL_TLS_CERT_PATH="/certs/client.crt"
```

## 🚨 Security Best Practices

1. **Never commit credentials**: Use `.env` files (gitignored) or secrets management
2. **Use strong API keys**: Generate with `openssl rand -hex 32`
3. **Enable TLS in production**: Always use HTTPS for public-facing servers
4. **Rotate credentials regularly**: Change API keys and regenerate TLS certificates
5. **Limit API key scope**: Use different keys for different environments
6. **Monitor Telegram messages**: Review notifications for security incidents

## 📚 Related Documentation

- [Client README](../vpn-sentinel-client/README.md)
- [Server README](../vpn-sentinel-server/README.md)
- [Deployment Guide](../deployments/README.md)
- [Refactor Plan](refactor-plan.md)
