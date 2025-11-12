#!/bin/bash
# Test client call script for VPN Sentinel server
# Usage: ./test_client_call.sh <server_url> <api_key> [client_id]
#   server_url: Full server URL with path (e.g., http://localhost:5000/api/v1) [REQUIRED]
#   api_key: API key for authentication [REQUIRED]
#   client_id: Client identifier (default: test-client-<timestamp>)
#
# Example:
#   ./test_client_call.sh "http://your-server:5000/api/v1" "your-api-key-here"
#   ./test_client_call.sh "http://localhost:5000/api/v1" "test-api-key" "my-client"

# Check required arguments
if [ $# -lt 2 ]; then
    echo "❌ Error: Missing required arguments"
    echo ""
    echo "Usage: $0 <server_url> <api_key> [client_id]"
    echo ""
    echo "Arguments:"
    echo "  server_url    Full server URL with path (REQUIRED)"
    echo "                Example: http://your-server:5000/api/v1"
    echo ""
    echo "  api_key       API key for authentication (REQUIRED)"
    echo "                Generate with: openssl rand -hex 32"
    echo ""
    echo "  client_id     Client identifier (optional)"
    echo "                Default: test-client-<timestamp>"
    echo ""
    echo "Example:"
    echo "  $0 \"http://localhost:5000/api/v1\" \"your-api-key-here\""
    echo ""
    exit 1
fi

# Required arguments
SERVER_URL="$1"
API_KEY="$2"

# Optional argument
CLIENT_ID="${3:-test-client-$(date +%s)}"

echo "🚀 Testing VPN Sentinel client call..."
echo "📡 Server: ${SERVER_URL}"
echo "🆔 Client ID: ${CLIENT_ID}"
echo "🔑 API Key: ${API_KEY}"
echo ""

# Get current timestamp
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Sample payload
PAYLOAD=$(cat <<EOF
{
  "client_id": "${CLIENT_ID}",
  "timestamp": "${TIMESTAMP}",
  "public_ip": "$(curl -s https://ipinfo.io/ip || echo '1.2.3.4')",
  "status": "alive",
  "location": {
    "country": "ES",
    "city": "Madrid", 
    "region": "Madrid",
    "org": "Test ISP",
    "timezone": "Europe/Madrid"
  },
  "dns_test": {
    "location": "ES",
    "colo": "MAD"
  }
}
EOF
)

echo "📦 Sending keepalive..."
curl -s -w "\n📊 HTTP Status: %{http_code}\n⏱️  Response Time: %{time_total}s\n\n" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d "${PAYLOAD}" \
  "${SERVER_URL}/keepalive"

echo "📋 Checking server status..."
curl -s -w "\n📊 HTTP Status: %{http_code}\n\n" \
  -H "X-API-Key: ${API_KEY}" \
  "${SERVER_URL}/status" | jq . 2>/dev/null || cat

echo "✅ Test completed!"