# Testing Instructions for Recent Changes

## Overview
This document provides instructions for testing the recent enhancements to VPN Sentinel.

## Changes Made (2025-11-10)

### Client Enhancements
1. **Geolocation provider logging**: VPN IP logs now show which provider was used
2. **Cleaner health monitor logs**: Shows script name instead of full container path

### Server Enhancements
1. **Version logging**: Server logs version and commit hash on startup
2. **Enhanced keepalive logs**: VPN info displayed when keepalive received
3. **New modules**: `version.py` and `server_utils.py` in `vpn_sentinel_common`
4. **Refactored entry point**: Server uses common utilities for cleaner code

### Documentation
1. **Environment variables**: Comprehensive guide at `docs/ENVIRONMENT_VARIABLES.md`
2. **Refactor plan updated**: Current status and deferred items documented

## Testing the Client

### Test 1: Geolocation Provider Logging

**Start the client and observe logs:**
```bash
docker compose up vpn-sentinel-client
```

**Expected output:**
```
INFO [vpn-info] 🌐 VPN IP: 1.2.3.4 (via ipinfo.io)
```
or
```
INFO [vpn-info] 🌐 VPN IP: 1.2.3.4 (via ip-api.com)
```

**Verify:** The geolocation provider name appears in parentheses after the IP address.

### Test 2: Health Monitor Log Clarity

**Start the client and observe startup logs:**
```bash
docker compose up vpn-sentinel-client
```

**Expected output:**
```
INFO [client] Starting health monitor: health_monitor_wrapper.py
```

**OLD (incorrect) output was:**
```
INFO [client] Starting health monitor: /app/vpn_sentinel_common/health_scripts/health_monitor_wrapper.py
```

**Verify:** Only the script filename is shown, not the full path.

## Testing the Server

### Test 3: Version Logging

**Start the server and observe startup logs:**
```bash
docker compose up vpn-sentinel-server
```

**Expected output:**
```
INFO [server] 🚀 Starting VPN Sentinel Server v1.0.0-dev-abc123f (commit: abc123f)
```

**Verify:** Version and commit hash are displayed on startup.

### Test 4: Enhanced Keepalive Logs

**Send a keepalive to the server:**
```bash
# With client running, wait for keepalive interval
docker compose logs -f vpn-sentinel-server
```

**Expected output:**
```
INFO [api] ✅ Keepalive from office-vpn-primary
INFO [vpn-info]   📍 Amsterdam, Netherlands | 🌐 1.2.3.4 | 🏢 Digital Ocean
```

**Verify:** VPN info is logged when keepalive is received.

### Test 5: Telegram Integration (Fully Implemented!)

**Test Telegram notifications and bot commands:**

#### A. Manual Test Script
```bash
# Set Telegram credentials
export TELEGRAM_BOT_TOKEN="your-bot-token-from-botfather"
export TELEGRAM_CHAT_ID="your-chat-id"

# Run test script
python3 tests/test_telegram_manual.py
```

**Expected:** Receives 5 test messages showing all notification types

#### B. Integration Test with Server
```bash
# Set credentials
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="your-chat-id"

# Start server (receives startup notification)
docker compose up vpn-sentinel-server

# Start client (receives client connected notification)
docker compose up vpn-sentinel-client
```

**Expected notifications:**
1. 🚀 Server startup message
2. ✅ Client connected message

**Expected logs:**
```
INFO [telegram] 🤖 Telegram bot is enabled
INFO [telegram] 📝 Registered command: /ping
INFO [telegram] 📝 Registered command: /status
INFO [telegram] 📝 Registered command: /help
INFO [telegram] ✅ Telegram bot polling started
INFO [telegram] 📤 Sending message: 🚀 VPN Keepalive Server Started...
INFO [telegram] ✅ Message sent successfully
```

#### C. Test Bot Commands

Send these messages in your Telegram chat:
- `/ping` - Test connectivity, get server info
- `/status` - Get detailed VPN client status
- `/help` - Show help message
- Any text - Get friendly response with command list

**Verify logs show:**
```
INFO [telegram] 📥 Received message (ID 123): /ping
INFO [telegram] 🎯 Processing command: /ping
INFO [telegram] 📤 Sending message: 🏓 Pong!...
INFO [telegram] ✅ Message sent successfully
```

#### D. Test IP Change Detection

```bash
# Connect client with one IP
docker compose up vpn-sentinel-client

# Wait for connection, then stop
docker compose stop vpn-sentinel-client

# Change VPN connection and restart
# (Or simulate by modifying geolocation response)
docker compose up vpn-sentinel-client
```

**Expected:** 🔄 VPN IP Changed notification if IP differs

### Test 6: Port Configuration (Already Working)

**Test custom ports:**
```bash
# Set custom ports
export VPN_SENTINEL_SERVER_API_PORT=5001
export VPN_SENTINEL_SERVER_HEALTH_PORT=8082
export VPN_SENTINEL_SERVER_DASHBOARD_PORT=8081

# Start server
docker compose up vpn-sentinel-server
```

**Expected logs:**
```
INFO [server] 🌐 Starting API server on 0.0.0.0:5001
INFO [server] 🌐 Starting Health server on 0.0.0.0:8082
INFO [server] 🌐 Starting Dashboard server on 0.0.0.0:8081
```

**Verify:** Server starts on custom ports.

## Integration Testing

### Test 7: Full Stack with Enhancements

**Start both client and server:**
```bash
# In terminal 1
docker compose up vpn-sentinel-server

# In terminal 2
docker compose up vpn-sentinel-client
```

**Observe both terminals for:**
1. ✅ Server shows version on startup
2. ✅ Client shows geolocation provider
3. ✅ Client shows clean health monitor log
4. ✅ Server logs VPN info when keepalive received
5. ✅ Both continue operating normally

## Unit Testing

**Run the existing test suite:**
```bash
./tests/run_tests.sh --unit
```

**Expected:** All tests pass (no new tests added, existing tests should still work)

## Linting

**Verify code quality:**
```bash
python3 -m flake8 vpn_sentinel_common/ vpn-sentinel-server/ vpn-sentinel-client/ \
  --max-line-length=120 --extend-ignore=E402
```

**Expected:** No errors (E402 ignored for path manipulation)

## Documentation Review

**Check new documentation:**
```bash
cat docs/ENVIRONMENT_VARIABLES.md
cat docs/refactor-plan.md
```

**Verify:**
- Environment variables guide is comprehensive
- Refactor plan is up to date with recent changes
- Deferred items are documented

## Rollback Plan

If any issues are found:

1. **Revert client changes:**
   ```bash
   git checkout HEAD~1 -- vpn-sentinel-client/vpn-sentinel-client.py
   ```

2. **Revert server changes:**
   ```bash
   git checkout HEAD~1 -- vpn-sentinel-server/vpn-sentinel-server.py
   git checkout HEAD~1 -- vpn_sentinel_common/api_routes.py
   ```

3. **Remove new modules:**
   ```bash
   git rm vpn_sentinel_common/version.py
   git rm vpn_sentinel_common/server_utils.py
   ```

## Notes

- All changes are backward compatible
- No breaking changes to APIs or data formats
- Telegram and port configuration were already working, just documented
- New utility modules are optional and only used by server entry point
