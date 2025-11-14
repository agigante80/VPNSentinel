#!/usr/bin/env bash
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
    local public_ip="$2"
    local dns_ip="$3"
    local location="$4"
    local provider="$5"
    local dns_location="${6:-$location}"  # DNS location (defaults to same as location)
    local last_seen="${7:-0}"
    
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
    "country": "${location}",
    "provider": "${provider}",
    "dns_test": {
        "dns_ip": "${dns_ip}",
        "dns_location": "${dns_location}",
        "dns_provider": "${provider}"
    },
    "client_version": "1.2.0"
}
EOF
)
    
    curl -sf -X POST \
        -H "Content-Type: application/json" \
        -d "${payload}" \
        "${BASE_URL}${API_PATH}/keepalive" > /dev/null
    
    echo "  ✓ ${client_id} (${location})"
}

echo "📡 Populating server with demo clients..."
echo ""

# Get server IP for red status detection
SERVER_IP=$(curl -sf http://localhost:5000/api/v1/status 2>/dev/null | grep -o '"server_ip":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
echo "   Server IP: ${SERVER_IP}"
echo ""

# Client 1: Green (Healthy) - Netherlands VPN, DNS matches location
send_keepalive \
    "office-vpn-primary" \
    "185.220.100.245" \
    "185.220.101.50" \
    "Netherlands" \
    "PrivacyVPN" \
    "0"

# Client 2: Green (Healthy) - Germany VPN, DNS matches location  
send_keepalive \
    "datacenter-vpn-backup" \
    "193.25.101.200" \
    "193.25.102.10" \
    "Germany" \
    "SecureNet" \
    "1"

# Client 3: Yellow (DNS Leak) - Sweden VPN but US DNS (Google)
send_keepalive \
    "home-network-vpn" \
    "91.200.12.45" \
    "8.8.8.8" \
    "Sweden" \
    "FastVPN" \
    "United States" \
    "3"

# Client 4: Red (VPN Bypass) - Same IP as server or home IP leak
send_keepalive \
    "mobile-vpn-device" \
    "${SERVER_IP}" \
    "${SERVER_IP}" \
    "United States" \
    "Comcast Cable" \
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
    SCREENSHOT_CMD="chromium-browser --headless --disable-gpu --screenshot='${SCREENSHOT_PATH}' --window-size=1600,1100 --hide-scrollbars --virtual-time-budget=5000 '${DASHBOARD_URL}'"
elif command -v chromium > /dev/null 2>&1; then
    SCREENSHOT_CMD="chromium --headless --disable-gpu --screenshot='${SCREENSHOT_PATH}' --window-size=1600,1100 --hide-scrollbars --virtual-time-budget=5000 '${DASHBOARD_URL}'"
elif command -v google-chrome > /dev/null 2>&1; then
    SCREENSHOT_CMD="google-chrome --headless --disable-gpu --screenshot='${SCREENSHOT_PATH}' --window-size=1600,1100 --hide-scrollbars --virtual-time-budget=5000 '${DASHBOARD_URL}'"
elif command -v firefox > /dev/null 2>&1; then
    SCREENSHOT_CMD="firefox --headless --screenshot '${SCREENSHOT_PATH}' --window-size=1600,1100 '${DASHBOARD_URL}'"
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
