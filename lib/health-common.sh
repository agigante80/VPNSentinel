#!/bin/sh
# VPN Sentinel Health Common Library
# Shared functions for health monitoring across VPN Sentinel components

# =============================================================================
# VPN Sentinel Health Common Library
# =============================================================================
#
# DESCRIPTION:
#   Common health check functions and utilities shared between health monitoring
#   scripts. Provides standardized health checks for client process, network
#   connectivity, server connectivity, and logging.
#
# SHARED FUNCTIONS:
#   - check_client_process: Check if main client script is running
#   - check_network_connectivity: Check external network connectivity
#   - check_server_connectivity: Check VPN Sentinel server connectivity
#   - log_message: Standardized logging with timestamps and levels
#   - log_info, log_error, log_warn: Convenience logging functions
#
# ENVIRONMENT VARIABLES:
#   - VPN_SENTINEL_URL: Server URL for connectivity checks
#   - VPN_SENTINEL_API_PATH: API path prefix (default: /api/v1)
#   - TZ: Timezone for timestamps (default: UTC)
#
# USAGE:
#   source lib/health-common.sh
#
# Author: VPN Sentinel Project
# License: MIT
# =============================================================================

# -----------------------------------------------------------------------------
# Logging Functions
# -----------------------------------------------------------------------------
log_message() {
    local level="$1"
    local component="$2"
    local message="$3"
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    echo "${timestamp} ${level} [${component}] ${message}" >&2
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

# -----------------------------------------------------------------------------
# Health Check Functions
# -----------------------------------------------------------------------------
check_client_process() {
    # Check if main client script is running
    if pgrep -f "vpn-sentinel-client.sh" > /dev/null 2>&1; then
        echo "healthy"
        return 0
    else
        echo "not_running"
        return 1
    fi
}

check_network_connectivity() {
    # Check external connectivity using Cloudflare
    if curl -f -s --max-time 5 "https://1.1.1.1/cdn-cgi/trace" > /dev/null 2>&1; then
        echo "healthy"
        return 0
    else
        echo "unreachable"
        return 1
    fi
}

check_server_connectivity() {
    # Check connectivity to VPN Sentinel server
    local server_url
    server_url="${VPN_SENTINEL_URL:-}"

    if [ -z "$server_url" ]; then
        echo "not_configured"
        return 0
    fi

    # Check server connectivity by testing if the server URL is reachable
    # Use a simple HEAD request to the base server URL
    if curl -s --max-time 10 -I "$server_url" > /dev/null 2>&1; then
        echo "healthy"
        return 0
    else
        echo "unreachable"
        return 1
    fi
}

check_dns_leak_detection() {
    # Check if DNS leak detection is functional
    # This is a basic check - full leak detection happens in main client
    if curl -f -s --max-time 5 "https://ipinfo.io/json" > /dev/null 2>&1; then
        echo "healthy"
        return 0
    else
        echo "unavailable"
        return 1
    fi
}

# -----------------------------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------------------------
get_system_info() {
    # Get basic system resource information
    local memory_percent
    memory_percent="unknown"

    local disk_percent
    disk_percent="unknown"

    # Get memory usage percentage
    if command -v free > /dev/null 2>&1; then
        memory_percent=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
    fi

    # Get disk usage percentage for root filesystem
    if command -v df > /dev/null 2>&1; then
        disk_percent=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    fi

    cat << EOF
{
  "memory_percent": "$memory_percent",
  "disk_percent": "$disk_percent"
}
EOF
}