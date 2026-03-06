# Telegram Integration Guide

VPN Sentinel includes comprehensive Telegram integration with automatic notifications and interactive bot commands.

## 📱 Features

### Automatic Notifications

The server automatically sends Telegram messages for key events:

1. **🚀 Server Started** - When the server starts up
2. **✅ Client Connected** - When a VPN client connects for the first time
3. **🔄 IP Changed** - When a client's VPN IP address changes
4. **⚠️ No Clients** - Alert when no VPN clients are connected

### Interactive Bot Commands

Send messages to your bot to get real-time information:

- `/ping` - Test connectivity and get server status
- `/status` - Get detailed VPN client status
- `/help` - Show available commands
- Any other text - Get a friendly response with command list

### Comprehensive Logging

Every Telegram interaction is logged:
- 📤 Outgoing messages (with preview)
- 📥 Incoming messages (with message ID)
- 🎯 Command processing
- ✅ Success/failure status

## 🔧 Setup

### 1. Create Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot`
3. Follow prompts to create your bot
4. Save the bot token (looks like `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Get Chat ID

**Method A: Using a helper bot**
1. Search for `@userinfobot` in Telegram
2. Start a conversation
3. Your chat ID will be displayed

**Method B: Using your bot**
1. Send a message to your new bot
2. Visit `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Find `"chat":{"id":-1001234567890}` in the JSON response

### 3. Configure Environment Variables

```bash
export TELEGRAM_BOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
export TELEGRAM_CHAT_ID="-1001234567890"
```

Or add to `.env` file:
```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=-1001234567890
```

### 4. Start Server

```bash
docker compose up vpn-sentinel-server
```

You should see:
```
INFO [telegram] 🤖 Telegram bot is enabled
INFO [telegram] 📝 Registered command: /ping
INFO [telegram] 📝 Registered command: /status
INFO [telegram] 📝 Registered command: /help
INFO [telegram] ✅ Telegram bot polling started
INFO [telegram] 📤 Sending message: 🚀 VPN Keepalive Server Started...
INFO [telegram] ✅ Message sent successfully
```

## 🧪 Testing

### Quick Test Script

```bash
python3 tests/test_telegram_manual.py
```

This sends test notifications for all message types.

### Manual Testing

1. **Test server startup:**
   ```bash
   docker compose up vpn-sentinel-server
   ```
   Expected: Receive server startup message

2. **Test client connect:**
   ```bash
   docker compose up vpn-sentinel-client
   ```
   Expected: Receive client connected message

3. **Test bot commands:**
   - Send `/ping` in Telegram
   - Send `/status` in Telegram
   - Send `/help` in Telegram

4. **Test IP change:**
   - Connect client
   - Change VPN server
   - Restart client
   Expected: Receive IP changed message

## 📬 Message Examples

### Server Started

```
🚀 VPN Keepalive Server Started

Server is now monitoring VPN connections.
Alert threshold: 15 minutes
Check interval: 5 minutes
🛡️ Security: Rate limiting (30 req/min)
🔐 API Auth: Enabled
Started at: 2025-11-10 22:00:00 UTC

💡 Send /ping to test the connection!
📊 Send /status for detailed VPN status
❓ Send /help for all commands
```

### Client Connected

```
✅ VPN Connected!

Client: synology-vpn-media
VPN IP: 185.72.199.129
📍 Location: Toruń, Kujawsko-Pomorskie, PL
🏢 Provider: AS50599 DATASPACE P.S.A.
🕒 VPN Timezone: Europe/Warsaw
Connected at: 2025-11-10 22:01:15 UTC

🔒 DNS Leak Test:
DNS Location: PL
DNS Server: WAW
✅ No DNS leak detected
```

### IP Changed

```
🔄 VPN IP Changed!

Previous IP: 185.72.199.129
Client: synology-vpn-media
VPN IP: 89.40.181.202
📍 Location: Warsaw, Mazowieckie, PL
🏢 Provider: AS12741 netia.pl
🕒 VPN Timezone: Europe/Warsaw
Connected at: 2025-11-10 22:05:30 UTC

🔒 DNS Leak Test:
DNS Location: PL
DNS Server: WAW
✅ No DNS leak detected
```

### No Clients Alert

```
⚠️ No VPN Clients Connected

No active VPN connections detected.
Time: 2025-11-10 22:10:00 UTC

💡 This alert will not repeat until a client connects and disconnects again.
```

### /ping Command Response

```
🏓 Pong!

Server time: 2025-11-10 22:15:00 UTC
Active clients: 1
Alert threshold: 15 minutes
Check interval: 5 minutes
```

### /status Command Response

```
📊 VPN Status

🟢 synology-vpn-media - Online
   IP: 89.40.181.202
   Location: Warsaw, Mazowieckie, PL
   Last seen: 2 minutes ago

Server time: 2025-11-10 22:16:45 UTC
```

### /help Command Response

```
❓ VPN Sentinel Bot Help

I monitor your VPN connections and send alerts.

Available Commands:

🏓 /ping
   Test bot connectivity and get server info

📊 /status
   Get detailed status of all VPN clients
   Shows IP, location, and last seen time

❓ /help
   Show this help message

Automatic Notifications:
• New client connects
• Client IP changes
• Client disconnects/timeout
• No clients connected

The bot monitors VPN connections 24/7 and sends alerts automatically.
```

### Unknown Command / Text

```
👋 Hello! I'm your VPN monitoring bot.

I received: hi

Use /help to see available commands.

Available commands:
🏓 /ping - Test connectivity
📊 /status - Get VPN status
❓ /help - Show help
```

## 🔍 Troubleshooting

### No Messages Received

1. **Check credentials:**
   ```bash
   echo $TELEGRAM_BOT_TOKEN
   echo $TELEGRAM_CHAT_ID
   ```

2. **Check server logs:**
   ```bash
   docker compose logs vpn-sentinel-server | grep telegram
   ```

3. **Look for:**
   - `⚠️ Telegram not configured` - Missing credentials
   - `❌ Failed to send message: HTTP 401` - Invalid bot token
   - `❌ Failed to send message: HTTP 400` - Invalid chat ID

### Bot Not Responding to Commands

1. **Check polling started:**
   ```
   INFO [telegram] ✅ Telegram bot polling started
   ```

2. **Check you're using the correct chat:**
   - Bot only responds to the configured CHAT_ID
   - Send `/start` to your bot first

3. **Check for errors:**
   ```bash
   docker compose logs vpn-sentinel-server | grep "telegram.*Error"
   ```

### Messages Not Logged

All messages should be logged. If not, check log level:
```bash
export VPN_SENTINEL_DEBUG="true"
```

## 🔒 Security Considerations

1. **Protect your bot token** - Never commit it to git
2. **Use a private chat** - Bot only works with configured CHAT_ID
3. **Monitor logs** - All interactions are logged for audit trail
4. **Rotate tokens** - Periodically regenerate bot token via @BotFather
5. **Limit chat access** - Only authorized users should have the CHAT_ID

## 📊 Monitoring

All Telegram activity is logged with component `[telegram]`:

```bash
# View all Telegram logs
docker compose logs vpn-sentinel-server | grep telegram

# View sent messages only
docker compose logs vpn-sentinel-server | grep "📤 Sending"

# View received messages only
docker compose logs vpn-sentinel-server | grep "📥 Received"

# View errors
docker compose logs vpn-sentinel-server | grep "telegram.*❌"
```

## 🚀 Advanced Usage

### Custom Notification Threshold

Edit `vpn-sentinel-server/vpn-sentinel-server.py`:
```python
telegram.notify_server_started(alert_threshold_min=30, check_interval_min=10)
```

### Disable Notifications

```bash
# Don't set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
unset TELEGRAM_BOT_TOKEN
unset TELEGRAM_CHAT_ID
```

Server will run normally but skip Telegram integration:
```
INFO [telegram] ⚠️ Telegram bot is disabled (no credentials configured)
```

### Silent Notifications

To send notifications without sound (useful for non-critical alerts):
```python
telegram.send_telegram_message("Your message", silent=True)
```

## 📚 API Reference

See `vpn_sentinel_common/telegram.py` for full API documentation:

- `notify_server_started(alert_threshold_min, check_interval_min)` - Server startup
- `notify_client_connected(client_id, vpn_ip, ...)` - Client connection
- `notify_ip_changed(client_id, old_ip, new_ip, ...)` - IP change
- `notify_no_clients()` - No clients alert
- `send_telegram_message(message, silent)` - Send custom message
- `register_command(command, handler)` - Register custom command
- `start_polling()` - Start bot polling loop

