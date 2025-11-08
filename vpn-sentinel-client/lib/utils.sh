#!/usr/bin/env bash
# Minimal compatibility utils for vpn-sentinel-client shell script.
# These functions are small, defensive implementations used by unit tests
# when the Python shims are not present.

json_escape() {
    # Escape backslashes and double quotes for embedding JSON in shell.
    # Usage: json_escape "${VAR}"
    if [ -z "$1" ]; then
        printf ''
        return 0
    fi
    printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

sanitize_string() {
    # Remove control characters and trim to 100 chars to match Python shim behavior.
    if [ -z "$1" ]; then
        printf ''
        return 0
    fi
    printf '%s' "$1" | tr -d '\000-\037' | head -c 100
}

load_config() {
    # Populate a small set of variables used by the shell client when the
    # canonical Python loader is not available. Keep behavior intentionally
    # simple and environment-driven to match test expectations.
    API_BASE_URL="${VPN_SENTINEL_URL:-http://your-server-url:5000}"
    API_PATH="${VPN_SENTINEL_API_PATH:-/api/v1}"
    SERVER_URL="${API_BASE_URL}${API_PATH}"
    TLS_CERT_PATH="${VPN_SENTINEL_TLS_CERT_PATH:-}"
    DEBUG="${VPN_SENTINEL_DEBUG:-false}"
    GEOLOCATION_SERVICE="${VPN_SENTINEL_GEOLOCATION_SERVICE:-auto}"
    INTERVAL="${INTERVAL:-300}"
    TIMEOUT="${TIMEOUT:-10}"
    CLIENT_ID="${VPN_SENTINEL_CLIENT_ID:-}"
    VPN_TIMEZONE="${VPN_TIMEZONE:-}"
    VPN_SENTINEL_API_KEY="${VPN_SENTINEL_API_KEY:-}"
}

export -f json_escape sanitize_string load_config >/dev/null 2>&1 || true
