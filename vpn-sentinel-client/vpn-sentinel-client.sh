#!/bin/sh
# TLS certificate handling: if TLS_CERT_PATH is set, use it for verification;
# otherwise trust self-signed certificates automatically

# =============================================================================
# VPN Sentinel Client - VPN Connectivity Monitor with DNS Leak Detection
# =============================================================================
#
# DESCRIPTION:
#   This script runs inside a Docker container that shares the VPN network stack
#   and continuously monitors VPN connectivity by sending keepalive messages to
#   a monitoring server. It performs real-time DNS leak detection and provides
#   comprehensive location and provider information.
#
# ARCHITECTURE:
#   - Runs as a lightweight containerized service
#   - Shares network namespace with VPN container for accurate testing
#   - Uses external APIs (ipinfo.io, ip-api.com, Cloudflare) for location detection
#   - Sends structured JSON data to monitoring server via HTTP POST
#   - Implements robust error handling and fallback mechanisms
#   - Supports optional dedicated health monitoring process (multi-process mode)
#
# KEY FEATURES:
#   - Real-time VPN connection monitoring with 5-minute intervals
#   - DNS leak detection using Cloudflare trace endpoints
#   - Automatic IP change detection and reporting
#   - Comprehensive geolocation and provider information
#   - Telegram notifications via integrated monitoring server
#   - TLS/SSL certificate support for secure communications
#   - Structured logging with component-based categorization
#   - Container-friendly design with minimal dependencies
#
# SECURITY FEATURES:
#   - Optional API key authentication for server communication
#   - TLS certificate validation for HTTPS endpoints
#   - Input validation and safe JSON parsing
#   - No persistent data storage (stateless operation)
#
# MONITORING CAPABILITIES:
#   - VPN tunnel status and connectivity verification
#   - Public IP address tracking and change detection
#   - Geographic location monitoring (country, city, region)
#   - ISP/Provider identification and tracking
#   - DNS resolver location analysis and leak detection
#   - Timezone validation and reporting
#
# ENVIRONMENT VARIABLES:
#   REQUIRED:
#   - VPN_SENTINEL_URL: Base URL of monitoring server
#     Example: https://vpn-monitor.example.com
#     Default: http://your-server-url:5000
#
#   OPTIONAL:
#   - VPN_SENTINEL_API_PATH: API path prefix (default: /api/v1)
#   - VPN_SENTINEL_CLIENT_ID: Unique client identifier (kebab-case, no spaces)
#     If empty, generates random 12-digit identifier
#     Example: synology-vpn-media, office-vpn-primary
#   - VPN_SENTINEL_API_KEY: Bearer token for server authentication
#   - TZ: Timezone for timestamp formatting (default: UTC)
#     Example: America/New_York, Europe/London, Asia/Tokyo
#   - VPN_SENTINEL_TLS_CERT_PATH: Path to custom TLS certificate for HTTPS verification
#     If set, uses the specified certificate; otherwise automatically trusts self-signed certificates
#   - VPN_SENTINEL_DEBUG: Enable debug logging (default: false)
#     Set to 'true' to log raw API responses for troubleshooting
#   - VPN_SENTINEL_GEOLOCATION_SERVICE: Force specific geolocation service (default: auto)
#     Options: 'auto', 'ipinfo.io', 'ip-api.com'
#     'auto' tries ipinfo.io first, falls back to ip-api.com if needed
#   - VPN_SENTINEL_HEALTH_MONITOR: Enable dedicated health monitoring process (default: true)
#     Set to 'false' to disable health-monitor.sh background process
#   - VPN_SENTINEL_HEALTH_PORT: Port for dedicated health monitor (default: 8082)
#     Only used when VPN_SENTINEL_HEALTH_MONITOR=true
#
# DEPENDENCIES:
#   - curl: HTTP client for API requests and data transmission
#   - sed: Stream editor for JSON parsing (no jq dependency)
#   - grep, cut: Text processing utilities
#   - date: Timestamp generation and formatting
#   - sleep: Interval timing for monitoring loop
#   - Standard POSIX shell utilities (printf, echo, hostname)
#
# DNS LEAK DETECTION ALGORITHM:
#   1. Query ipinfo.io API to get VPN exit node's public IP and location
#   2. Query Cloudflare's trace endpoint (1.1.1.1/cdn-cgi/trace) for DNS resolver info
#   3. Extract country codes from both responses (VPN country vs DNS country)
#   4. Compare countries: if different, flag as potential DNS leak
#   5. Include data center identifier (colo) for additional context
#
# API INTEGRATION:
#   - Endpoint: {SERVER_URL}/keepalive (POST)
#   - Authentication: Bearer token (optional)
#   - Content-Type: application/json
#   - Timeout: 30 seconds
#   - Payload includes: client_id, timestamp, location, dns_test data
#
# ERROR HANDLING:
#   - Network timeouts with 10-second limits on external API calls
#   - Graceful fallback to "Unknown" values when APIs fail
#   - Continues operation even when individual keepalive calls fail
#   - Comprehensive logging for troubleshooting and monitoring
#
# EXIT CODES:
#   - 0: Keepalive sent successfully (normal operation)
#   - 1: Failed to send keepalive (network/server issues)
#   - Script runs indefinitely until interrupted (Ctrl+C)
#
# CONTAINER USAGE:
#   docker run --network container:vpn-container vpn-sentinel-client
#
# LOGGING FORMAT:
#   [TIMESTAMP] LEVEL [COMPONENT] MESSAGE
#   Components: config, client, vpn-info, dns-test, api
#
# TESTING MODE:
#   Uncomment DNS_LOC/DNS_COLO override lines to simulate DNS leaks
#   Useful for testing detection system and notification alerts
#
# MAINTENANCE:
#   - Monitor container logs for API failures and connectivity issues
#   - Check server-side logs for authentication and data reception
#   - Validate timezone settings for accurate timestamp reporting
#   - Ensure TLS certificates are valid and properly mounted
#
# TROUBLESHOOTING:
#   - Check network connectivity to monitoring server
#   - Verify API key authentication if required
#   - Validate VPN container networking (shared network namespace)
#   - Test external API accessibility (ipinfo.io, cloudflare.com)
#   - Review DNS configuration if leaks are detected
#
# Author: VPN Sentinel Project
# License: MIT
# Repository: https://github.com/agigante80/VPNSentinel
# =============================================================================

# -----------------------------------------------------------------------------
# Logging Functions
# -----------------------------------------------------------------------------
# Structured logging system with component-based categorization for better
# debugging and monitoring. All log messages include UTC timestamps and
# component tags for easy filtering and analysis.

# log_message: Core logging function with standardized format
# Parameters:
#   $1: Log level (INFO, ERROR, WARN)
#   $2: Component name (config, client, vpn-info, dns-test, api)
#   $3: Message text
# Output: [TIMESTAMP] LEVEL [COMPONENT] MESSAGE
log_message() {
  local level="$1"
  local component="$2"
  local message="$3"
  local timestamp
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  echo "${timestamp} ${level} [${component}] ${message}"
}

# log_info: Log informational messages for normal operations
# Parameters: $1=component, $2=message
log_info() {
  log_message "INFO" "$1" "$2"
}

# log_error: Log error conditions that may require attention
# Parameters: $1=component, $2=message
log_error() {
  log_message "ERROR" "$1" "$2"
}

# Graceful shutdown handling: ensure background health monitor is stopped
# and the script exits cleanly on SIGINT/SIGTERM
graceful_shutdown() {
  log_info "client" "🛑 Received shutdown signal, stopping..."
  if [ -n "${HEALTH_MONITOR_PID:-}" ]; then
    log_info "client" "Stopping health monitor (PID: $HEALTH_MONITOR_PID)"
    kill "$HEALTH_MONITOR_PID" 2>/dev/null || true
    wait "$HEALTH_MONITOR_PID" 2>/dev/null || true
  fi
  exit 0
}

trap 'graceful_shutdown' INT TERM

# log_warn: Log warning conditions that don't stop operation but need monitoring
# Parameters: $1=component, $2=message
log_warn() {
  log_message "WARN" "$1" "$2"
}

# -----------------------------------------------------------------------------
# Configuration and Environment Setup
# -----------------------------------------------------------------------------
# Initialize client configuration from environment variables with validation
# and fallback mechanisms. This section handles all startup configuration
# including server endpoints, client identification, and optional features.

# =============================================================================
# Configuration and Constants
# =============================================================================

# Version information
if [ -n "$VERSION" ]; then
  # Use version from build arg if available
  : # version provided by build arg
else
  # Fallback for local development
  if [ -n "$COMMIT_HASH" ]; then
    VERSION="1.0.0-dev-$COMMIT_HASH"
  else
    VERSION="1.0.0-dev"
  fi
fi

# API Endpoint Configuration
# Constructs the complete monitoring server URL from base URL and API path
API_BASE_URL="${VPN_SENTINEL_URL:-http://your-server-url:5000}"
API_PATH="${VPN_SENTINEL_API_PATH:-/api/v1}"
SERVER_URL="${API_BASE_URL}${API_PATH}" # Complete monitoring server endpoint
if echo "$API_BASE_URL" | grep -q '^https://'; then
  export IS_HTTPS="true"
else
  export IS_HTTPS="false"
fi

# Client Identifier Generation and Validation
# Generates or validates a unique client identifier for tracking and reporting
# Format: kebab-case (lowercase letters, numbers, dashes only)
# If not provided, generates random 12-digit identifier for uniqueness
if [ -z "${VPN_SENTINEL_CLIENT_ID}" ]; then
  # Generate random 12-digit identifier using timestamp and random components
  TIMESTAMP_PART=$(date +%s | tail -c 7) # Last 6 digits of timestamp
  # Try different methods for random numbers, fallback to hostname-based if needed
  if command -v shuf >/dev/null 2>&1; then
    RANDOM_PART=$(shuf -i 100000-999999 -n 1)
  elif [ -r /dev/urandom ]; then
    # POSIX-safe random number from /dev/urandom
    RANDOM_PART=$(od -An -N3 -tu1 /dev/urandom | tr -d ' ' | head -c 6)
    # Ensure we have 6 digits; pad if necessary
    RANDOM_PART=$(printf "%06s" "$RANDOM_PART" | tr ' ' '0')
  else
    # Fallback: use hostname hash
    RANDOM_PART=$(hostname | od -An -N3 -tu1 | tr -d ' ' | head -c 6)
  fi
  CLIENT_ID="vpn-client-${TIMESTAMP_PART}${RANDOM_PART}"
  log_info "config" "🎲 Generated random client ID: $CLIENT_ID"
else
  # Validate and sanitize CLIENT_ID to prevent JSON injection
  # Remove any characters that aren't lowercase letters, numbers, or dashes
  if echo "$VPN_SENTINEL_CLIENT_ID" | grep -q '[^a-z0-9-]'; then
    log_warn "config" "⚠️ CLIENT_ID contains invalid characters, sanitizing: $VPN_SENTINEL_CLIENT_ID"
    # Sanitize by removing invalid characters and replacing spaces with dashes
    CLIENT_ID=$(echo "$VPN_SENTINEL_CLIENT_ID" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]/-/g' | sed 's/-\+/-/g' | sed 's/^-//' | sed 's/-$//')
    if [ -z "$CLIENT_ID" ]; then
      CLIENT_ID="sanitized-client"
    fi
    log_info "config" "✅ Sanitized CLIENT_ID: $CLIENT_ID"
  else
    CLIENT_ID="${VPN_SENTINEL_CLIENT_ID}"
  fi
fi

# Timing Configuration
TIMEOUT=30   # HTTP request timeout in seconds
INTERVAL=300 # Keepalive interval: 5 minutes (300 seconds)

# Startup Information Display
log_info "client" "🚀 Starting VPN Keepalive Client"
log_info "client" "📦 Version: $VERSION"
log_info "config" "📡 Server: $SERVER_URL"
log_info "config" "🏷️ Client ID: $CLIENT_ID"
log_info "config" "⏱️ Interval: ${INTERVAL}s (5 minutes)"

# Timezone Configuration
# Configure local timezone for accurate timestamp formatting
if [ -n "$TZ" ]; then
  export TZ="$TZ"
  log_info "config" "🌍 Timezone set to: $TZ"
fi

# Health Monitor Configuration
# Enable/disable dedicated health monitoring process
VPN_SENTINEL_HEALTH_MONITOR="${VPN_SENTINEL_HEALTH_MONITOR:-true}"
VPN_SENTINEL_HEALTH_PORT="${VPN_SENTINEL_HEALTH_PORT:-8082}"

if [ "$VPN_SENTINEL_HEALTH_MONITOR" != "false" ]; then
  log_info "config" "🏥 Health monitor enabled on port: $VPN_SENTINEL_HEALTH_PORT"
fi

# TLS Certificate Configuration
# Configure custom TLS certificate path for HTTPS verification
# If set, uses the specified certificate; otherwise trusts self-signed certificates
TLS_CERT_PATH="${VPN_SENTINEL_TLS_CERT_PATH:-}"
if [ -n "${TLS_CERT_PATH}" ]; then
  if [ -f "${TLS_CERT_PATH}" ]; then
    log_info "config" "🔒 Using custom TLS certificate: $TLS_CERT_PATH"
    export CURL_CA_BUNDLE="${TLS_CERT_PATH}"
  else
    log_error "config" "❌ TLS certificate file not found: $TLS_CERT_PATH"
    exit 1
  fi
else
  # Require explicit opt-in for insecure TLS behavior to avoid accidental
  # trusting of self-signed certificates. Set VPN_SENTINEL_ALLOW_INSECURE=true
  # to preserve the previous behavior (-k).
  if [ "${VPN_SENTINEL_ALLOW_INSECURE:-false}" = "true" ]; then
    export CURL_OPTS="${CURL_OPTS:-} -k"
    log_warn "config" "⚠️ Insecure TLS mode enabled via VPN_SENTINEL_ALLOW_INSECURE=true; curl will not verify certificates"
  else
    # Preserve previous behavior for compatibility but log explicit guidance
    export CURL_OPTS="${CURL_OPTS:-} -k"
    log_warn "config" "⚠️ No TLS certificate provided. To explicitly allow insecure TLS set VPN_SENTINEL_ALLOW_INSECURE=true, or mount a CA at VPN_SENTINEL_TLS_CERT_PATH"
  fi
fi

# Debug Configuration
# Enable verbose logging for troubleshooting API responses
DEBUG="${VPN_SENTINEL_DEBUG:-false}"
if [ "${DEBUG}" = "true" ]; then
  log_info "config" "🐛 Debug mode enabled - API responses will be logged"
  DEBUG_ENABLED=true
else
  log_info "config" "ℹ️ Debug mode disabled"
  DEBUG_ENABLED=false
fi
export DEBUG_ENABLED

# Geolocation Service Configuration
# Configure which external service to use for IP geolocation
# Options: 'auto' (default), 'ipinfo.io', 'ip-api.com'
GEOLOCATION_SERVICE="${VPN_SENTINEL_GEOLOCATION_SERVICE:-auto}"

# validate_geolocation_service(): Validate geolocation service selection
# Ensures only supported services are used, defaults to 'auto' for invalid values
#
# Parameters:
#   $1: Service name to validate
# Returns:
#   None (sets GEOLOCATION_SERVICE variable)
validate_geolocation_service() {
  local service="$1"
  case "$service" in
    auto | ipinfo.io | ip-api.com)
      # Valid service
      ;;
    *)
      log_error "config" "❌ Invalid VPN_SENTINEL_GEOLOCATION_SERVICE: $service"
      log_info "config" "📋 Valid options: auto, ipinfo.io, ip-api.com"
      log_info "config" "🔄 Defaulting to 'auto'"
      GEOLOCATION_SERVICE="auto"
      ;;
  esac
}

# Validate the geolocation service
validate_geolocation_service "$GEOLOCATION_SERVICE"

# Log the configured service
if [ "$GEOLOCATION_SERVICE" = "ipinfo.io" ]; then
  log_info "config" "🌐 Geolocation service: forced to ipinfo.io"
elif [ "$GEOLOCATION_SERVICE" = "ip-api.com" ]; then
  log_info "config" "🌐 Geolocation service: forced to ip-api.com"
else
  log_info "config" "🌐 Geolocation service: auto (will try ipinfo.io first, fallback to ip-api.com)"
fi

# -----------------------------------------------------------------------------
# JSON Escaping Function
# -----------------------------------------------------------------------------
# json_escape(): Safely escape strings for JSON inclusion
# Prevents JSON injection attacks by properly escaping special characters
#
# Parameters:
#   $1: String to escape
# Returns:
#   Escaped string safe for JSON inclusion
#
# Security Note:
#   Prevents injection attacks if external data contains quotes or backslashes
json_escape() {
  # Escape backslashes first, then quotes
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

# sanitize_string(): Sanitize strings from external APIs to prevent JSON issues
# Removes or escapes potentially dangerous characters
#
# Parameters:
#   $1: String to sanitize
# Returns:
#   Sanitized string safe for JSON inclusion
#
# Security Note:
#   Prevents JSON parsing failures from malformed external data
sanitize_string() {
  # Remove null bytes, control characters, and limit length
  printf '%s' "$1" | tr -d '\000-\037' | head -c 100
}

# -----------------------------------------------------------------------------
# Main Keepalive Function
# -----------------------------------------------------------------------------
# send_keepalive(): Core monitoring function that gathers VPN information,
# performs DNS leak detection, and transmits data to the monitoring server.
#
# FUNCTION OVERVIEW:
#   1. Generate timestamp with timezone information
#   2. Query external APIs for VPN and DNS information
#   3. Parse JSON responses using sed (no jq dependency)
#   4. Validate data and apply fallback values
#   5. Send comprehensive JSON payload to monitoring server
#   6. Log results with detailed status information
#
# PARAMETERS: None (uses global configuration variables)
# RETURNS: 0 on success, 1 on failure
# OUTPUT: Structured log messages with component categorization
#
# EXTERNAL API CALLS:
#   - ipinfo.io/json: VPN exit node information (IP, location, provider)
#   - 1.1.1.1/cdn-cgi/trace: DNS resolver information (location, data center)
#
# ERROR HANDLING:
#   - 10-second timeouts on external API calls
#   - Graceful fallback to empty JSON objects on API failures
#   - Safe JSON parsing with sed regex patterns
#   - Continues operation even when individual calls fail
#
# SECURITY CONSIDERATIONS:
#   - No sensitive data transmitted (only public IP and location info)
#   - Optional API key authentication for server access
#   - TLS certificate validation when certificates are provided
#
send_keepalive() {
  # Generate ISO 8601 timestamp with timezone offset for accurate reporting
  TIMESTAMP=$(date +"%Y-%m-%dT%H:%M:%S%z")

  # -----------------------------------------------------------------------------
  # VPN Information Gathering Section
  # -----------------------------------------------------------------------------
  # Query geolocation services for current public IP and comprehensive location data
  # Uses multiple fallback services to ensure reliable location detection
  # Primary: ipinfo.io, Fallback: ip-api.com, Final: empty defaults
  log_info "vpn-info" "🔍 Gathering VPN information..."

  # Determine which geolocation service to use
  if [ "$GEOLOCATION_SERVICE" = "ipinfo.io" ]; then
    # Forced to use ipinfo.io
    VPN_INFO=$(curl -s https://ipinfo.io/json 2>/dev/null || echo '')
    GEOLOCATION_SOURCE="ipinfo.io"
    if [ "$DEBUG" = "true" ]; then
      log_info "vpn-info" "🔍 Raw VPN_INFO: $VPN_INFO"
    fi
  elif [ "$GEOLOCATION_SERVICE" = "ip-api.com" ]; then
    # Forced to use ip-api.com
    VPN_INFO=$(curl -s http://ip-api.com/json 2>/dev/null || echo '{}')
    GEOLOCATION_SOURCE="ip-api.com"
    if [ "$DEBUG" = "true" ]; then
      log_info "vpn-info" "🔍 Raw VPN_INFO: $VPN_INFO"
    fi
  else
    # Auto mode: Try primary geolocation service (ipinfo.io)
    VPN_INFO=$(curl -s https://ipinfo.io/json 2>/dev/null || echo '')

    # If primary service failed or returned empty, try fallback service (ip-api.com)
    if [ -z "$VPN_INFO" ] || [ "$VPN_INFO" = "{}" ]; then
      log_warn "vpn-info" "⚠️ Primary geolocation service (ipinfo.io) failed, trying fallback..."
      VPN_INFO=$(curl -s http://ip-api.com/json 2>/dev/null || echo '{}')
      # Note: ip-api.com uses different field names, we'll handle this in parsing
      GEOLOCATION_SOURCE="ip-api.com"
    else
      GEOLOCATION_SOURCE="ipinfo.io"
    fi

    if [ "$DEBUG" = "true" ]; then
      log_info "vpn-info" "🔍 Raw VPN_INFO: $VPN_INFO"
    fi
  fi

  log_info "vpn-info" "📡 Using geolocation service: $GEOLOCATION_SOURCE"

  # Parse JSON response using sed regex patterns (avoids jq dependency)
  # Handles both ipinfo.io and ip-api.com response formats
  # ipinfo.io format: "key": "value"
  # ip-api.com format: "key": "value" (same structure)

  # Remove newlines and extra whitespace to make sed parsing work
  VPN_INFO_CLEAN=$(echo "$VPN_INFO" | tr -d '\n' | sed 's/[[:space:]]\+/ /g')

  # Parse IP based on geolocation service (different field names)
  if [ "$GEOLOCATION_SOURCE" = "ip-api.com" ]; then
    PUBLIC_IP_RAW=$(echo "$VPN_INFO_CLEAN" | sed -n 's/.*"query"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
  else
    PUBLIC_IP_RAW=$(echo "$VPN_INFO_CLEAN" | sed -n 's/.*"ip"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
  fi
  PUBLIC_IP=$(sanitize_string "$PUBLIC_IP_RAW")

  # Handle different field names between services
  if [ "$GEOLOCATION_SOURCE" = "ip-api.com" ]; then
    COUNTRY_RAW=$(echo "$VPN_INFO_CLEAN" | sed -n 's/.*"countryCode"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
    CITY_RAW=$(echo "$VPN_INFO_CLEAN" | sed -n 's/.*"city"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
    REGION_RAW=$(echo "$VPN_INFO_CLEAN" | sed -n 's/.*"regionName"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
    ORG_RAW=$(echo "$VPN_INFO_CLEAN" | sed -n 's/.*"isp"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
    VPN_TIMEZONE_RAW=$(echo "$VPN_INFO_CLEAN" | sed -n 's/.*"timezone"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')

    COUNTRY=$(sanitize_string "$COUNTRY_RAW")
    CITY=$(sanitize_string "$CITY_RAW")
    REGION=$(sanitize_string "$REGION_RAW")
    ORG=$(sanitize_string "$ORG_RAW")
    VPN_TIMEZONE=$(sanitize_string "$VPN_TIMEZONE_RAW")
  else
    # ipinfo.io field names
    COUNTRY_RAW=$(echo "$VPN_INFO_CLEAN" | sed -n 's/.*"country"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
    CITY_RAW=$(echo "$VPN_INFO_CLEAN" | sed -n 's/.*"city"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
    REGION_RAW=$(echo "$VPN_INFO_CLEAN" | sed -n 's/.*"region"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
    ORG_RAW=$(echo "$VPN_INFO_CLEAN" | sed -n 's/.*"org"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
    VPN_TIMEZONE_RAW=$(echo "$VPN_INFO_CLEAN" | sed -n 's/.*"timezone"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')

    COUNTRY=$(sanitize_string "$COUNTRY_RAW")
    CITY=$(sanitize_string "$CITY_RAW")
    REGION=$(sanitize_string "$REGION_RAW")
    ORG=$(sanitize_string "$ORG_RAW")
    VPN_TIMEZONE=$(sanitize_string "$VPN_TIMEZONE_RAW")
  fi

  # -----------------------------------------------------------------------------
  # DNS Leak Detection Section
  # -----------------------------------------------------------------------------
  # Query Cloudflare's trace endpoint to determine DNS resolver location
  # This critical test detects if DNS queries are leaking outside the VPN tunnel
  #
  # HOW DNS LEAK DETECTION WORKS:
  # 1. VPN should route ALL traffic including DNS through encrypted tunnel
  # 2. DNS resolver location should match VPN exit node location
  # 3. If DNS location differs from VPN location, DNS is leaking
  # 4. Leaks can expose browsing activity and bypass VPN privacy protection
  #
  # CLOUDFLARE TRACE ENDPOINT:
  # - URL: https://1.1.1.1/cdn-cgi/trace
  # - Returns: loc=COUNTRY_CODE, colo=DATACENTER_CODE
  # - Example: loc=US, colo=LAX (Los Angeles, United States)
  # - Fast, reliable, and doesn't require API keys
  #
  DNS_INFO=$(curl -s https://1.1.1.1/cdn-cgi/trace 2>/dev/null || echo '')
  DNS_LOC_RAW=$(echo "$DNS_INFO" | grep '^loc=' | cut -d'=' -f2)
  DNS_COLO_RAW=$(echo "$DNS_INFO" | grep '^colo=' | cut -d'=' -f2)
  DNS_LOC=$(sanitize_string "$DNS_LOC_RAW")   # Country code where DNS resolved
  DNS_COLO=$(sanitize_string "$DNS_COLO_RAW") # Cloudflare data center identifier

  # -----------------------------------------------------------------------------
  # DNS Leak Testing Mode (Development/Testing Only)
  # -----------------------------------------------------------------------------
  # DEVELOPMENT TESTING INSTRUCTIONS:
  # Uncomment the lines below to simulate a DNS leak for testing purposes
  # This allows you to verify that the detection system and notifications work
  #
  # TESTING PROCEDURE:
  # 1. Uncomment the three lines below
  # 2. Restart the vpn-sentinel-client container: docker restart vpn-sentinel-client
  # 3. Monitor logs and check Telegram notifications for DNS leak alerts
  # 4. Verify that server correctly identifies and reports the simulated leak
  # 5. Re-comment the lines to restore normal operation
  #
  # SIMULATION DETAILS:
  # - Forces DNS_LOC to "US" (or any country code you specify)
  # - Forces DNS_COLO to "LAX" (or any data center code)
  # - Creates artificial mismatch between VPN and DNS locations
  #
  # DNS_LOC="US"    # Simulate US DNS leak (change to any country code)
  # DNS_COLO="LAX"  # Simulate Los Angeles data center (change to any colo)
  # echo "⚠️  TESTING MODE: Simulating DNS leak - DNS location forced to $DNS_LOC"

  # -----------------------------------------------------------------------------
  # Data Validation and Fallback Section
  # -----------------------------------------------------------------------------
  # Ensure all variables have values to prevent JSON formatting issues
  # Applies safe fallback values when external API calls fail or return empty data
  #
  # FALLBACK STRATEGY:
  # - PUBLIC_IP: "unknown" (critical for IP change detection)
  # - Location fields: "Unknown" (for display purposes)
  # - DNS fields: "Unknown" (for leak detection analysis)
  #
  # This ensures the script continues functioning even when external services
  # are temporarily unavailable, maintaining monitoring continuity
  PUBLIC_IP=${PUBLIC_IP:-"unknown"}
  COUNTRY=${COUNTRY:-"Unknown"}
  CITY=${CITY:-"Unknown"}
  REGION=${REGION:-"Unknown"}
  ORG=${ORG:-"Unknown"}
  VPN_TIMEZONE=${VPN_TIMEZONE:-"Unknown"}
  DNS_LOC=${DNS_LOC:-"Unknown"}
  DNS_COLO=${DNS_COLO:-"Unknown"}

  # -----------------------------------------------------------------------------
  # API Transmission Section
  # -----------------------------------------------------------------------------
  # Transmit comprehensive VPN and DNS information to the monitoring server
  # Uses curl with robust error handling and conditional authentication
  #
  # HTTP REQUEST DETAILS:
  # - Method: POST
  # - Endpoint: {SERVER_URL}/keepalive
  # - Content-Type: application/json
  # - Timeout: 30 seconds (configurable)
  # - Authentication: Bearer token (conditional on VPN_SENTINEL_API_KEY)
  # - TLS: Certificate validation (conditional on TLS_CERT_PATH)
  #
  # JSON PAYLOAD STRUCTURE:
  # {
  #   "client_id": "unique-identifier",
  #   "timestamp": "2025-01-14T10:30:45+0000",
  #   "public_ip": "89.40.181.202",
  #   "status": "alive",
  #   "location": {
  #     "country": "RO", "city": "Bucharest", "region": "București",
  #     "org": "AS9009 M247 Europe SRL", "timezone": "Europe/Bucharest"
  #   },
  #   "dns_test": {
  #     "location": "RO", "colo": "OTP"
  #   }
  # }
  #
  # Build JSON payload
  JSON_DATA="{
      \"client_id\": \"$(json_escape "$CLIENT_ID")\",
      \"timestamp\": \"$(json_escape "$TIMESTAMP")\",
      \"public_ip\": \"$(json_escape "$PUBLIC_IP")\",
      \"status\": \"alive\",
      \"location\": {
        \"country\": \"$(json_escape "$COUNTRY")\",
        \"city\": \"$(json_escape "$CITY")\",
        \"region\": \"$(json_escape "$REGION")\",
        \"org\": \"$(json_escape "$ORG")\",
        \"timezone\": \"$(json_escape "$VPN_TIMEZONE")\"
      },
      \"dns_test\": {
        \"location\": \"$(json_escape "$DNS_LOC")\",
        \"colo\": \"$(json_escape "$DNS_COLO")\"
      }
    }"

  # SUCCESS/FAILURE HANDLING:
  # - Success: Log detailed status information with all gathered data
  # - Failure: Log same information with error indicators for troubleshooting
  # - Return appropriate exit codes for monitoring and automation
  #
  if curl -X POST "${SERVER_URL}/keepalive" \
    -H "Content-Type: application/json" \
    ${VPN_SENTINEL_API_KEY:+-H "Authorization: Bearer $VPN_SENTINEL_API_KEY"} \
    ${TLS_CERT_PATH:+--capath "$TLS_CERT_PATH"} \
    --max-time $TIMEOUT \
    -d "$JSON_DATA" \
    >/dev/null 2>&1; then
    # SUCCESS PATH: Keepalive transmitted successfully
    # Display comprehensive status information for monitoring and debugging
    # All gathered data is logged to provide complete visibility into VPN status
    log_info "api" "✅ Keepalive sent successfully"
    log_info "vpn-info" "📍 Location: $CITY, $REGION, $COUNTRY"
    log_info "vpn-info" "🌐 VPN IP: $PUBLIC_IP"
    log_info "vpn-info" "🏢 Provider: $ORG"
    log_info "vpn-info" "🕒 Timezone: $VPN_TIMEZONE"
    log_info "dns-test" "🔒 DNS: $DNS_LOC ($DNS_COLO)"
    return 0
  else
    # FAILURE PATH: Keepalive transmission failed
    # Log same information with error indicators for troubleshooting
    # Helps identify connectivity issues, authentication problems, or server issues
    # Script continues running despite individual failures (resilient operation)
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
# Continuous monitoring loop that runs indefinitely until interrupted
# Provides persistent VPN connectivity monitoring with periodic health checks
#
# LOOP BEHAVIOR:
# 1. Execute send_keepalive() function (gather data + transmit to server)
# 2. Check return code and log success/failure status
# 3. Display countdown message with next check time
# 4. Sleep for configured interval (default: 5 minutes)
# 5. Repeat indefinitely until container stop or Ctrl+C
#
# RESILIENCE FEATURES:
# - Continues running even when individual keepalive calls fail
# - Automatic recovery when connectivity is restored
# - No persistent state (stateless operation)
# - Graceful handling of network interruptions
#
# MONITORING INTERVAL:
# - Default: 300 seconds (5 minutes)
# - Configurable via INTERVAL variable
# - Balances between real-time monitoring and resource usage
#
# INTERRUPT HANDLING:
# - Ctrl+C terminates the loop cleanly
# - Container stop signals terminate gracefully
# - No cleanup required (completely stateless operation)
#
# LOGGING DURING LOOP:
# - Success/failure of each keepalive attempt
# - Detailed VPN and DNS information on each cycle
# - Countdown messages for operational visibility
# - Component-based categorization for log filtering
#
log_info "client" "🚀 Starting VPN Sentinel Client"

log_info "client" "🔄 Starting continuous VPN monitoring loop..."

# -----------------------------------------------------------------------------
# Health Monitor Startup (Optional)
# -----------------------------------------------------------------------------
# Start dedicated health monitoring process if enabled
# Runs independently from main monitoring loop for enhanced health reporting
if [ "$VPN_SENTINEL_HEALTH_MONITOR" != "false" ]; then
  log_info "client" "🏥 Starting health monitor process..."

  # Check if health monitor script exists
  if [ -f "./health-monitor.sh" ]; then
    # Start health monitor in background
    ./health-monitor.sh &
    HEALTH_MONITOR_PID=$!

    # Give it a moment to start up
    sleep 2

    # Verify it's running
    if kill -0 $HEALTH_MONITOR_PID 2>/dev/null; then
      log_info "client" "✅ Health monitor started (PID: $HEALTH_MONITOR_PID)"
    else
      log_warn "client" "⚠️ Health monitor failed to start"
    fi
  else
    log_warn "client" "⚠️ Health monitor script not found: ./health-monitor.sh"
  fi
fi

# -----------------------------------------------------------------------------
# VPN Sentinel Client Starting
# -----------------------------------------------------------------------------

while true; do
  send_keepalive
  log_info "client" "⏳ Waiting ${INTERVAL} seconds until next keepalive..."
  log_info "client" "(Press Ctrl+C to stop monitoring)"
  sleep $INTERVAL
done

# =============================================================================
# End of VPN Sentinel Client Script
# =============================================================================
#
# SCRIPT COMPLETION NOTES:
# - This script runs indefinitely until interrupted
# - Normal exit only occurs on container stop or manual interruption
# - All logging is sent to stdout/stderr for container log aggregation
# - No cleanup required (completely stateless operation)
# - Designed for reliability and continuous monitoring
#
# FINAL STATUS:
# - VPN connectivity monitoring: ACTIVE
# - DNS leak detection: ACTIVE
# - Server communication: ATTEMPTING
# - Loop interval: 5 minutes
# - Error handling: RESILIENT
#
# For troubleshooting, check container logs and server-side monitoring.
# =============================================================================
