#!/bin/sh

# =============================================================================
# VPN Keepalive Client with DNS Leak Detection
# =============================================================================
# 
# This script monitors VPN connectivity and detects DNS leaks by periodically
# sending keepalive messages to a monitoring server. It runs inside a Docker
# container that shares the VPN network stack, allowing it to test if traffic
# is properly routing through the VPN tunnel.
#
# Features:
# - Real-time VPN connection monitoring
# - DNS leak detection using Cloudflare trace endpoints
# - Telegram notifications via keepalive server
# - Automatic IP change detection
# - Comprehensive location and provider information
# - Robust error handling and fallback values
#
# Environment Variables:
# - KEEPALIVE_SERVER_URL: URL of the monitoring server (required)
# - KEEPALIVE_CLIENT_ID: Unique identifier for this client (default: synology-vpn-media)
# - KEEPALIVE_API_KEY: Optional API key for server authentication
# - TZ: Timezone for timestamp formatting (default: system timezone)
#
# Dependencies:
# - curl: For HTTP requests to APIs and monitoring server
# - sed: For JSON parsing (no jq dependency for minimal container compatibility)
# - Standard POSIX shell utilities (date, grep, cut, sleep)
#
# DNS Leak Detection Logic:
# 1. Gets VPN IP and location from ipinfo.io
# 2. Gets DNS resolver location from Cloudflare's trace endpoint
# 3. Compares VPN country with DNS country
# 4. Reports mismatches as potential DNS leaks
#
# Exit Codes:
# - 0: Keepalive sent successfully
# - 1: Failed to send keepalive (network/server issues)
#
# Author: VPN Sentinel Project
# License: MIT
# =============================================================================

# -----------------------------------------------------------------------------
# Configuration and Environment Setup
# -----------------------------------------------------------------------------

SERVER_URL="${KEEPALIVE_SERVER_URL}"                    # Monitoring server endpoint
CLIENT_ID="${KEEPALIVE_CLIENT_ID:-synology-vpn-media}"  # Unique client identifier
TIMEOUT=30                                              # HTTP request timeout (seconds)
INTERVAL=300                                            # Keepalive interval (5 minutes)

# Display startup information
echo "🚀 Starting VPN Keepalive Client"
echo "📡 Server: $SERVER_URL"
echo "🏷️  Client ID: $CLIENT_ID"
echo "⏱️  Interval: ${INTERVAL}s (5 minutes)"
echo ""

# Configure timezone if specified
if [ -n "$TZ" ]; then
    export TZ="$TZ"
    echo "🌍 Timezone set to: $TZ"
fi

# -----------------------------------------------------------------------------
# Main Keepalive Function
# -----------------------------------------------------------------------------
# Gathers VPN information, performs DNS leak test, and sends data to server
send_keepalive() {
    # Generate ISO 8601 timestamp with timezone
    TIMESTAMP=$(date +"%Y-%m-%dT%H:%M:%S%z")
    
    # -----------------------------------------------------------------------------
    # VPN Information Gathering
    # -----------------------------------------------------------------------------
    # Query ipinfo.io for current public IP and geolocation data
    # This shows where the VPN exit server is located
    echo "🔍 Gathering VPN information..."
    VPN_INFO=$(curl -s --max-time 10 https://ipinfo.io/json 2>/dev/null || echo '{}')
    
    # Parse JSON response using sed (avoids jq dependency for container compatibility)
    # Extracts key-value pairs using regex pattern matching
    PUBLIC_IP=$(echo "$VPN_INFO" | sed -n 's/.*"ip"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
    COUNTRY=$(echo "$VPN_INFO" | sed -n 's/.*"country"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
    CITY=$(echo "$VPN_INFO" | sed -n 's/.*"city"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
    REGION=$(echo "$VPN_INFO" | sed -n 's/.*"region"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
    ORG=$(echo "$VPN_INFO" | sed -n 's/.*"org"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
    VPN_TIMEZONE=$(echo "$VPN_INFO" | sed -n 's/.*"timezone"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
    
    # -----------------------------------------------------------------------------
    # DNS Leak Detection Test
    # -----------------------------------------------------------------------------
    # Query Cloudflare's trace endpoint to determine DNS resolver location
    # If DNS requests leak outside VPN, this will show a different location
    DNS_INFO=$(curl -s --max-time 10 https://1.1.1.1/cdn-cgi/trace 2>/dev/null || echo '')
    DNS_LOC=$(echo "$DNS_INFO" | grep '^loc=' | cut -d'=' -f2)      # Country code where DNS resolved
    DNS_COLO=$(echo "$DNS_INFO" | grep '^colo=' | cut -d'=' -f2)    # Cloudflare data center identifier
    
    # -----------------------------------------------------------------------------
    # DNS Leak Testing Mode (for development/testing)
    # -----------------------------------------------------------------------------
    # Uncomment the lines below to simulate a DNS leak for testing the detection system
    # This forces the DNS location to appear as if it's coming from a different country
    # 
    # TESTING INSTRUCTIONS:
    # 1. Uncomment the three lines below
    # 2. Restart the keepalive-client container: docker restart keepalive-client
    # 3. Monitor logs and Telegram notifications for DNS leak alerts
    # 4. Re-comment the lines to restore normal operation
    #
    # DNS_LOC="US"    # Simulate US DNS leak (change to any country code)
    # DNS_COLO="LAX"  # Simulate Los Angeles data center (change to any colo)
    # echo "⚠️  TESTING MODE: Simulating DNS leak - DNS location forced to $DNS_LOC"
    
    # -----------------------------------------------------------------------------
    # Data Validation and Fallback Values
    # -----------------------------------------------------------------------------
    # Ensure all variables have values to prevent JSON formatting issues
    # Uses "unknown"/"Unknown" as fallback when API calls fail or return empty data
    PUBLIC_IP=${PUBLIC_IP:-"unknown"}
    COUNTRY=${COUNTRY:-"Unknown"}
    CITY=${CITY:-"Unknown"}
    REGION=${REGION:-"Unknown"}
    ORG=${ORG:-"Unknown"}
    VPN_TIMEZONE=${VPN_TIMEZONE:-"Unknown"}
    DNS_LOC=${DNS_LOC:-"Unknown"}
    DNS_COLO=${DNS_COLO:-"Unknown"}
    
    # -----------------------------------------------------------------------------
    # Send Keepalive Data to Monitoring Server
    # -----------------------------------------------------------------------------
    # Transmits comprehensive VPN and DNS information to the monitoring server
    # Includes conditional API key authentication if KEEPALIVE_API_KEY is set
    # JSON payload contains both VPN location data and DNS leak test results
    if curl -X POST \
      --max-time $TIMEOUT \
      --silent \
      --fail \
      -H "Content-Type: application/json" \
      ${KEEPALIVE_API_KEY:+-H "Authorization: Bearer $KEEPALIVE_API_KEY"} \
      -d "{
        \"client_id\": \"$CLIENT_ID\",
        \"timestamp\": \"$TIMESTAMP\",
        \"public_ip\": \"$PUBLIC_IP\",
        \"status\": \"alive\",
        \"location\": {
          \"country\": \"$COUNTRY\",
          \"city\": \"$CITY\",
          \"region\": \"$REGION\",
          \"org\": \"$ORG\",
          \"timezone\": \"$VPN_TIMEZONE\"
        },
        \"dns_test\": {
          \"location\": \"$DNS_LOC\",
          \"colo\": \"$DNS_COLO\"
        }
      }" \
      "$SERVER_URL/keepalive" >/dev/null 2>&1; then
        # Success: Display formatted status information
        echo "✅ Keepalive sent successfully at $(date)"
        echo "   📍 Location: $CITY, $REGION, $COUNTRY"
        echo "   🌐 VPN IP: $PUBLIC_IP"
        echo "   🏢 Provider: $ORG"
        echo "   🕒 Timezone: $VPN_TIMEZONE"
        echo "   🔒 DNS: $DNS_LOC ($DNS_COLO)"
        return 0
    else
        # Failure: Display same information but with error indicator
        # Helps with troubleshooting by showing what data was available
        echo "❌ Failed to send keepalive to $SERVER_URL at $(date)"
        echo "   📍 Location: $CITY, $REGION, $COUNTRY"
        echo "   🌐 VPN IP: $PUBLIC_IP"
        echo "   🏢 Provider: $ORG"
        echo "   🕒 Timezone: $VPN_TIMEZONE"
        echo "   🔒 DNS: $DNS_LOC ($DNS_COLO)"
        return 1
    fi
}

# -----------------------------------------------------------------------------
# Main Execution Loop
# -----------------------------------------------------------------------------
# Continuously monitors VPN connection by sending periodic keepalive messages
# Runs indefinitely until container is stopped or script is interrupted
# 
# Loop behavior:
# 1. Execute keepalive function (gather data + send to server)
# 2. Display wait message with countdown information
# 3. Sleep for configured interval (default: 5 minutes)
# 4. Repeat indefinitely
#
# The script will continue running even if individual keepalive attempts fail,
# ensuring continuous monitoring and automatic recovery when connectivity is restored
echo ""
echo "🔄 Starting continuous VPN monitoring loop..."
echo ""

while true; do
    send_keepalive
    echo ""
    echo "⏳ Waiting ${INTERVAL} seconds until next keepalive..."
    echo "   (Press Ctrl+C to stop monitoring)"
    sleep $INTERVAL
done

# =============================================================================
# End of VPN Sentinel Client Script
# =============================================================================