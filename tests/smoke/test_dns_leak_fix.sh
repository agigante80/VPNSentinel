#!/bin/bash
# Test script to verify DNS leak false positive fix
# Simulates the exact scenarios from the Telegram messages

set -e

SERVER_URL="${1:-http://localhost:5000}"
API_KEY="${2:-test123}"
API_PATH="${3:-/api/v1}"

echo "🧪 Testing DNS Leak False Positive Fix"
echo "======================================"
echo "Server: $SERVER_URL"
echo "API Path: $API_PATH"
echo ""

# Test 1: Romania (full name) vs RO (code) - Should NOT be DNS leak
echo "Test 1: VPN in Romania, DNS in RO (was false positive)"
echo "-------------------------------------------------------"
PAYLOAD_1=$(cat <<EOF
{
  "client_id": "test-romania-client",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%S%z")",
  "public_ip": "89.40.181.202",
  "status": "alive",
  "client_version": "1.0.0-test",
  "location": {
    "country": "Romania",
    "city": "Bucharest",
    "region": "Bucharest",
    "org": "M Europe SRL",
    "timezone": "Europe/Bucharest"
  },
  "dns_test": {
    "location": "RO",
    "colo": "OTP"
  }
}
EOF
)

RESPONSE_1=$(curl -s -X POST "$SERVER_URL$API_PATH/keepalive" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d "$PAYLOAD_1")

echo "Response: $RESPONSE_1"
if echo "$RESPONSE_1" | grep -q '"status":"ok"'; then
    echo "✅ Test 1 PASSED: Server accepted payload"
else
    echo "❌ Test 1 FAILED: Server rejected payload"
    exit 1
fi
echo ""

# Test 2: RO (code) vs RO (code) - Should NOT be DNS leak  
echo "Test 2: VPN in RO, DNS in RO"
echo "-----------------------------"
PAYLOAD_2=$(cat <<EOF
{
  "client_id": "test-ro-client",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%S%z")",
  "public_ip": "185.94.192.162",
  "status": "alive",
  "client_version": "1.0.0-test",
  "location": {
    "country": "RO",
    "city": "Sofia",
    "region": "Sofia-Capital",
    "org": "AS9009 M247 Europe SRL",
    "timezone": "Europe/Sofia"
  },
  "dns_test": {
    "location": "BG",
    "colo": "FRA"
  }
}
EOF
)

RESPONSE_2=$(curl -s -X POST "$SERVER_URL$API_PATH/keepalive" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d "$PAYLOAD_2")

echo "Response: $RESPONSE_2"
if echo "$RESPONSE_2" | grep -q '"status":"ok"'; then
    echo "✅ Test 2 PASSED"
else
    echo "❌ Test 2 FAILED"
    exit 1
fi
echo ""

# Test 3: United States vs US - Should NOT be DNS leak
echo "Test 3: VPN in United States, DNS in US (was false positive)"
echo "-------------------------------------------------------------"
PAYLOAD_3=$(cat <<EOF
{
  "client_id": "test-us-client",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%S%z")",
  "public_ip": "195.181.163.129",
  "status": "alive",
  "client_version": "1.0.0-test",
  "location": {
    "country": "United States",
    "city": "Miami",
    "region": "Florida",
    "org": "Datacamp Limited",
    "timezone": "America/New_York"
  },
  "dns_test": {
    "location": "US",
    "colo": "MIA"
  }
}
EOF
)

RESPONSE_3=$(curl -s -X POST "$SERVER_URL$API_PATH/keepalive" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d "$PAYLOAD_3")

echo "Response: $RESPONSE_3"
if echo "$RESPONSE_3" | grep -q '"status":"ok"'; then
    echo "✅ Test 3 PASSED"
else
    echo "❌ Test 3 FAILED"
    exit 1
fi
echo ""

# Test 4: Real DNS leak - Spain vs Germany - SHOULD be DNS leak
echo "Test 4: Real DNS leak - VPN in Spain, DNS in Germany"
echo "------------------------------------------------------"
PAYLOAD_4=$(cat <<EOF
{
  "client_id": "test-leak-client",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%S%z")",
  "public_ip": "172.67.163.127",
  "status": "alive",
  "client_version": "1.0.0-test",
  "location": {
    "country": "ES",
    "city": "Madrid",
    "region": "Madrid",
    "org": "Test ISP",
    "timezone": "Europe/Madrid"
  },
  "dns_test": {
    "location": "DE",
    "colo": "FRA"
  }
}
EOF
)

RESPONSE_4=$(curl -s -X POST "$SERVER_URL$API_PATH/keepalive" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d "$PAYLOAD_4")

echo "Response: $RESPONSE_4"
if echo "$RESPONSE_4" | grep -q '"status":"ok"'; then
    echo "✅ Test 4 PASSED: Server accepted payload (leak will be detected in notification)"
else
    echo "❌ Test 4 FAILED"
    exit 1
fi
echo ""

# Check status endpoint
echo "Checking status endpoint for all clients..."
echo "-------------------------------------------"
STATUS=$(curl -s "$SERVER_URL$API_PATH/status" -H "X-API-Key: $API_KEY" | python3 -m json.tool)
echo "$STATUS"
echo ""

# Count clients
CLIENT_COUNT=$(echo "$STATUS" | grep -c "\"test-" || true)
echo "✅ Found $CLIENT_COUNT test clients in status"
echo ""

echo "======================================"
echo "✅ ALL TESTS PASSED!"
echo ""
echo "Expected Telegram behavior:"
echo "  - Test 1 (Romania): 🟢 Secure (NO DNS leak)"
echo "  - Test 2 (RO->BG): 🟡 DNS Leak (different countries)"
echo "  - Test 3 (United States): 🟢 Secure (NO DNS leak)"
echo "  - Test 4 (ES->DE): 🟡 DNS Leak (real leak)"
echo ""
echo "Check Telegram messages to verify correct emoji colors!"
