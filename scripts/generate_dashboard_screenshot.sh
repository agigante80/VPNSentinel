#!/usr/bin/env bash
# shellcheck shell=bash
# Generate dashboard screenshot with demo data showing different client statuses
# Creates: 1 red (VPN bypass), 1 yellow (DNS leak), 2 green (healthy)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
API_PORT="${VPN_SENTINEL_SERVER_API_PORT:-5000}"
HEALTH_PORT="${VPN_SENTINEL_SERVER_HEALTH_PORT:-8081}"
DASHBOARD_PORT="${VPN_SENTINEL_SERVER_DASHBOARD_PORT:-8080}"
API_PATH="${VPN_SENTINEL_API_PATH:-/api/v1}"
BASE_URL="http://localhost:${API_PORT}"
HEALTH_URL="http://localhost:${HEALTH_PORT}"
DASHBOARD_URL="http://localhost:${DASHBOARD_PORT}/dashboard"
SCREENSHOT_PATH="${ROOT_DIR}/docs/images/dashboard-screenshot.png"

echo "🖼️  VPN Sentinel Dashboard Screenshot Generator"
echo "================================================"
echo ""

# Check if server is running
if ! curl -sf "${HEALTH_URL}/health" > /dev/null 2>&1; then
    echo "❌ Server not running (health check at ${HEALTH_URL}/health failed)"
    echo "Please start the server first:"
    echo "  cd ${ROOT_DIR}"
    echo "  PYTHONPATH=${ROOT_DIR} python3 vpn-sentinel-server/vpn-sentinel-server.py"
    exit 1
fi

echo "✅ Server is running"
echo "   API: ${BASE_URL}"
echo "   Dashboard: ${DASHBOARD_URL}"
echo ""

# Function to send keepalive
send_keepalive() {
    local client_id="$1"
    local client_version="$2"
    local public_ip="$3"
    local city="$4"
    local region="$5"
    local country="$6"
    local provider="$7"
    local dns_country="$8"
    local dns_colo="$9"
    local last_seen="${10:-0}"
    
    # Calculate timestamp for last_seen minutes ago
    local timestamp
    if [ "$(uname)" = "Darwin" ]; then
        # macOS
        timestamp=$(date -u -v-"${last_seen}M" +"%Y-%m-%dT%H:%M:%SZ")
    else
        # Linux
        timestamp=$(date -u -d "${last_seen} minutes ago" +"%Y-%m-%dT%H:%M:%SZ")
    fi
    
    local payload
    payload=$(cat <<EOF
{
    "client_id": "${client_id}",
    "timestamp": "${timestamp}",
    "public_ip": "${public_ip}",
    "city": "${city}",
    "region": "${region}",
    "country": "${country}",
    "provider": "${provider}",
    "dns_loc": "${dns_country}",
    "dns_colo": "${dns_colo}",
    "client_version": "${client_version}"
}
EOF
)
    
    curl -sf -X POST \
        -H "Content-Type: application/json" \
        -d "${payload}" \
        "${BASE_URL}${API_PATH}/keepalive" > /dev/null
    
    echo "  ✓ ${client_id} (${city}, ${country})"
}

echo "📡 Populating server with demo clients..."
echo ""

# Get server IP for red status detection
# We'll fetch the dashboard to get the actual server IP displayed there
echo "   Fetching server information from dashboard..."
SERVER_IP=$(curl -sf "${DASHBOARD_URL}" 2>/dev/null | grep -oP 'Server IP:\s*<code>\K[^<]+' || echo "unknown")
if [ "${SERVER_IP}" = "unknown" ] || [ -z "${SERVER_IP}" ]; then
    # Fallback: try to get from ipinfo.io
    SERVER_IP=$(curl -sf https://ipinfo.io/ip 2>/dev/null || echo "203.0.113.10")
fi
echo "   Server IP: ${SERVER_IP}"
echo ""

# Client 1: Green (Healthy) - USA VPN, DNS matches location
# vpn-media-usa 1.0.0-dev-8aa4ecc 45.130.86.7 New York City, New York, US AS42201 PVDataNet AB DNS US / EWR
send_keepalive \
    "vpn-media-usa" \
    "1.0.0-dev-8aa4ecc" \
    "45.130.86.7" \
    "New York City" \
    "New York" \
    "US" \
    "AS42201 PVDataNet AB" \
    "US" \
    "EWR" \
    "0"

# Client 2: Green (Healthy) - Bulgaria VPN, DNS matches location
# vpn-media Unknown 185.94.192.162 Sofia, Sofia-city, Bulgaria M LTD Sofia Infrastructure DNS BG / FRA
send_keepalive \
    "vpn-media" \
    "Unknown" \
    "185.94.192.162" \
    "Sofia" \
    "Sofia-city" \
    "BG" \
    "M LTD Sofia Infrastructure" \
    "BG" \
    "FRA" \
    "1"

# Client 3: Yellow (DNS Leak) - Netherlands VPN but US DNS leak
send_keepalive \
    "office-vpn-primary" \
    "1.2.0" \
    "185.220.100.245" \
    "Amsterdam" \
    "North Holland" \
    "NL" \
    "PrivacyGuard BV" \
    "US" \
    "IAD" \
    "3"

# Client 4: Red (VPN Bypass) - Same IP as server (home ISP connection leaked)
# This simulates when VPN fails and client connects with home IP
send_keepalive \
    "home-network-leaked" \
    "1.1.5" \
    "${SERVER_IP}" \
    "Chicago" \
    "Illinois" \
    "US" \
    "Comcast Cable Communications" \
    "US" \
    "ORD" \
    "7"

echo ""
echo "✅ Demo clients populated"
echo ""

# Wait longer for server to process and calculate statuses
echo "⏳ Waiting for server to calculate client statuses (15 seconds)..."
sleep 15

# Check for screenshot tools
SCREENSHOT_CMD=""

if command -v chromium-browser > /dev/null 2>&1; then
    SCREENSHOT_CMD="chromium-browser --headless --disable-gpu --screenshot='${SCREENSHOT_PATH}' --window-size=1600,950 --hide-scrollbars --virtual-time-budget=5000 '${DASHBOARD_URL}'"
elif command -v chromium > /dev/null 2>&1; then
    SCREENSHOT_CMD="chromium --headless --disable-gpu --screenshot='${SCREENSHOT_PATH}' --window-size=1600,950 --hide-scrollbars --virtual-time-budget=5000 '${DASHBOARD_URL}'"
elif command -v google-chrome > /dev/null 2>&1; then
    SCREENSHOT_CMD="google-chrome --headless --disable-gpu --screenshot='${SCREENSHOT_PATH}' --window-size=1600,950 --hide-scrollbars --virtual-time-budget=5000 '${DASHBOARD_URL}'"
elif command -v firefox > /dev/null 2>&1; then
    SCREENSHOT_CMD="firefox --headless --screenshot '${SCREENSHOT_PATH}' --window-size=1600,950 '${DASHBOARD_URL}'"
else
    echo "❌ No headless browser found (chromium, chrome, or firefox)"
    echo ""
    echo "Install one of:"
    echo "  sudo apt install chromium-browser    # Debian/Ubuntu"
    echo "  sudo dnf install chromium             # Fedora"
    echo "  brew install chromium                 # macOS"
    echo ""
    echo "Or manually take a screenshot of:"
    echo "  ${DASHBOARD_URL}"
    echo ""
    echo "Dashboard is ready for manual screenshot!"
    exit 0
fi

echo "📸 Capturing screenshot..."
echo "   URL: ${DASHBOARD_URL}"
echo "   Output: ${SCREENSHOT_PATH}"
echo ""

# Take screenshot
eval "${SCREENSHOT_CMD}"

if [ -f "${SCREENSHOT_PATH}" ]; then
    FILE_SIZE=$(du -h "${SCREENSHOT_PATH}" | cut -f1)
    echo ""
    echo "✅ Screenshot saved successfully!"
    echo "   File: ${SCREENSHOT_PATH}"
    echo "   Size: ${FILE_SIZE}"
    echo ""
    echo "Preview with:"
    echo "   xdg-open '${SCREENSHOT_PATH}'  # Linux"
    echo "   open '${SCREENSHOT_PATH}'      # macOS"
else
    echo "❌ Screenshot failed"
    exit 1
fi

echo ""
echo "🎉 Dashboard screenshot generation complete!"
echo ""
echo "Next steps:"
echo "  1. Review the screenshot: ${SCREENSHOT_PATH}"
echo "  2. Commit: git add ${SCREENSHOT_PATH}"
echo "  3. Commit: git commit -m 'docs: Update dashboard screenshot'"
