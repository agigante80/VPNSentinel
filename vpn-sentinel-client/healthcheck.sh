#!/bin/sh
# Health check script for VPN Sentinel Client
# Verifies that the client is running and can communicate with the server

# Check if the main script is running
if ! pgrep -f "vpn-sentinel-client.sh" > /dev/null; then
    echo "❌ VPN Sentinel client script is not running"
    exit 1
fi

# Check if we can reach external services for DNS leak detection
if ! curl -f -s --max-time 5 "https://1.1.1.1/cdn-cgi/trace" > /dev/null 2>&1; then
    echo "❌ Cannot reach Cloudflare for DNS leak detection"
    exit 1
fi

# Check if we can reach the monitoring server (if URL is configured)
# This is a warning, not a failure - client can still be healthy if server is temporarily down
SERVER_WARNING=""
if [ -n "$VPN_SENTINEL_URL" ]; then
    # Try to connect to the server
    if ! curl -f -s --max-time 10 "$VPN_SENTINEL_URL/api/v1/health" > /dev/null 2>&1; then
        SERVER_WARNING="⚠️ Cannot reach VPN Sentinel server at $VPN_SENTINEL_URL (client will retry)"
    fi
fi

if [ -n "$SERVER_WARNING" ]; then
    echo "✅ VPN Sentinel client is healthy"
    echo "$SERVER_WARNING"
else
    echo "✅ VPN Sentinel client is healthy"
fi

exit 0