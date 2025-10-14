
#!/bin/sh
# Trust self-signed certificates (true/false)
TRUST_SELF_SIGNED_CERTIFICATES="${TRUST_SELF_SIGNED_CERTIFICATES:-false}"

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
# - VPN_SENTINEL_SERVER_API_BASE_URL: Base URL of the monitoring server (required)
# - VPN_SENTINEL_SERVER_API_PATH: API path prefix (default: /api/v1)
# - VPN_SENTINEL_CLIENT_ID: Unique identifier for this client (kebab-case, no spaces)
#   If empty, generates random 12-digit identifier (default: synology-vpn-media)
# - VPN_SENTINEL_API_KEY: Optional API key for server authentication
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

# Structured logging function with component tags
log_message() {
    local level="$1"
    local component="$2"
    local message="$3"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    echo "${timestamp} ${level} [${component}] ${message}"
}

log_info() {
    log_message "INFO" "$1" "$2"
}

log_error() {
    log_message "ERROR" "$1" "$2"
}

log_warn() {
    log_message "WARN" "$1" "$2"
}

# Construct full API endpoint URL
API_BASE_URL="${VPN_SENTINEL_SERVER_API_BASE_URL}"
API_PATH="${VPN_SENTINEL_SERVER_API_PATH:-/api/v1}"
SERVER_URL="${API_BASE_URL}${API_PATH}"                         # Complete monitoring server endpoint

# Client identifier validation and generation
# If VPN_SENTINEL_CLIENT_ID is empty, generate a random 12-digit identifier
if [ -z "${VPN_SENTINEL_CLIENT_ID}" ]; then
    # Generate random 12-digit identifier using timestamp and container hostname
    TIMESTAMP_PART=$(date +%s | tail -c 7)  # Last 6 digits of timestamp
    # Try different methods for random numbers, fallback to hostname-based if needed
    if command -v shuf >/dev/null 2>&1; then
        RANDOM_PART=$(shuf -i 100000-999999 -n 1)
    elif [ -n "$RANDOM" ]; then
        RANDOM_PART=$(printf "%06d" $((RANDOM % 900000 + 100000)))
    else
        # Fallback: use hostname hash
        RANDOM_PART=$(hostname | od -An -N3 -tu1 | tr -d ' ' | head -c 6)
    fi
    CLIENT_ID="vpn-client-${TIMESTAMP_PART}${RANDOM_PART}"
    log_info "config" "🎲 Generated random client ID: $CLIENT_ID"
else
    # Validate kebab-case format (lowercase with dashes, no spaces)
    if echo "$VPN_SENTINEL_CLIENT_ID" | grep -q '[^a-z0-9-]'; then
        log_warn "config" "⚠️ CLIENT_ID should be kebab-case (lowercase, dashes only): $VPN_SENTINEL_CLIENT_ID"
    fi
    CLIENT_ID="${VPN_SENTINEL_CLIENT_ID}"
fi
TIMEOUT=30                                              # HTTP request timeout (seconds)
INTERVAL=300                                            # Keepalive interval (5 minutes)

# Display startup information
log_info "client" "🚀 Starting VPN Keepalive Client"
log_info "config" "📡 Server: $SERVER_URL"
log_info "config" "🏷️ Client ID: $CLIENT_ID"
log_info "config" "⏱️ Interval: ${INTERVAL}s (5 minutes)"

# Configure timezone if specified
if [ -n "$TZ" ]; then
    export TZ="$TZ"
    log_info "config" "🌍 Timezone set to: $TZ"
fi

# TLS certificate for HTTPS
TLS_CERT_PATH="${VPN_SENTINEL_TLS_CERT_PATH:-}"
if [ -n "$TLS_CERT_PATH" ]; then
    log_info "config" "🔒 TLS certificate enabled for HTTPS: $TLS_CERT_PATH"
else
    log_info "config" "⚠️ No TLS certificate provided; HTTPS verification disabled (using default curl behavior)"
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
    log_info "vpn-info" "🔍 Gathering VPN information..."
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
    # 2. Restart the vpn-sentinel-client container: docker restart vpn-sentinel-client
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
    # Includes conditional API key authentication if VPN_SENTINEL_API_KEY is set
    # JSON payload contains both VPN location data and DNS leak test results
    if curl -X POST \
      --max-time $TIMEOUT \
      --silent \
      --fail \
      -H "Content-Type: application/json" \
      ${VPN_SENTINEL_API_KEY:+-H "Authorization: Bearer $VPN_SENTINEL_API_KEY"} \
      ${TLS_CERT_PATH:+--cacert "$TLS_CERT_PATH"} \
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
        log_info "api" "✅ Keepalive sent successfully"
        log_info "vpn-info" "📍 Location: $CITY, $REGION, $COUNTRY"
        log_info "vpn-info" "🌐 VPN IP: $PUBLIC_IP"
        log_info "vpn-info" "🏢 Provider: $ORG"
        log_info "vpn-info" "🕒 Timezone: $VPN_TIMEZONE"
        log_info "dns-test" "🔒 DNS: $DNS_LOC ($DNS_COLO)"
        return 0
    else
        # Failure: Display same information but with error indicator
        # Helps with troubleshooting by showing what data was available
        log_error "api" "❌ Failed to send keepalive to $SERVER_URL"
        log_error "vpn-info" "📍 Location: $CITY, $REGION, $COUNTRY"
        log_error "vpn-info" "🌐 VPN IP: $PUBLIC_IP"
        log_error "vpn-info" "🏢 Provider: $ORG"
        log_error "vpn-info" "🕒 Timezone: $VPN_TIMEZONE"
        log_error "dns-test" "🔒 DNS: $DNS_LOC ($DNS_COLO)"
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
log_info "client" "🔄 Starting continuous VPN monitoring loop..."

while true; do
    send_keepalive
    log_info "client" "⏳ Waiting ${INTERVAL} seconds until next keepalive..."
    log_info "client" "(Press Ctrl+C to stop monitoring)"
    sleep $INTERVAL
done

# =============================================================================
# End of VPN Sentinel Client Script
# =============================================================================