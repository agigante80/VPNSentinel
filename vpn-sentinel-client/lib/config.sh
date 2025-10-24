#!/bin/sh
# Configuration helpers for VPN Sentinel client
# Sourced by vpn-sentinel-client.sh

# load_config: read env vars and set defaults
load_config() {
  # Version
  if [ -n "$VERSION" ]; then
    :
  else
    if [ -n "$COMMIT_HASH" ]; then
      VERSION="1.0.0-dev-$COMMIT_HASH"
    else
      VERSION="1.0.0-dev"
    fi
  fi

  API_BASE_URL="${VPN_SENTINEL_URL:-http://your-server-url:5000}"
  API_PATH="${VPN_SENTINEL_API_PATH:-/api/v1}"
  SERVER_URL="${API_BASE_URL}${API_PATH}"
  if echo "$API_BASE_URL" | grep -q '^https://'; then
    export IS_HTTPS="true"
  else
    export IS_HTTPS="false"
  fi

  TIMEOUT=30
  INTERVAL=300

  # Client ID
  if [ -z "${VPN_SENTINEL_CLIENT_ID}" ]; then
    TIMESTAMP_PART=$(date +%s | tail -c 7)
    if command -v shuf >/dev/null 2>&1; then
      RANDOM_PART=$(shuf -i 100000-999999 -n 1)
    elif [ -r /dev/urandom ]; then
      RANDOM_PART=$(od -An -N3 -tu1 /dev/urandom | tr -d ' ' | head -c 6)
      RANDOM_PART=$(printf "%06s" "$RANDOM_PART" | tr ' ' '0')
    else
      RANDOM_PART=$(hostname | od -An -N3 -tu1 | tr -d ' ' | head -c 6)
    fi
    CLIENT_ID="vpn-client-${TIMESTAMP_PART}${RANDOM_PART}"
    log_info "config" "🎲 Generated random client ID: $CLIENT_ID"
  else
    if echo "$VPN_SENTINEL_CLIENT_ID" | grep -q '[^a-z0-9-]'; then
      log_warn "config" "⚠️ CLIENT_ID contains invalid characters, sanitizing: $VPN_SENTINEL_CLIENT_ID"
      CLIENT_ID=$(echo "$VPN_SENTINEL_CLIENT_ID" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]/-/g' | sed 's/-\+/-/g' | sed 's/^-//' | sed 's/-$//')
      if [ -z "$CLIENT_ID" ]; then
        CLIENT_ID="sanitized-client"
      fi
      log_info "config" "✅ Sanitized CLIENT_ID: $CLIENT_ID"
    else
      CLIENT_ID="$VPN_SENTINEL_CLIENT_ID"
    fi
  fi

  VPN_SENTINEL_HEALTH_MONITOR="${VPN_SENTINEL_HEALTH_MONITOR:-true}"
  VPN_SENTINEL_HEALTH_PORT="${VPN_SENTINEL_HEALTH_PORT:-8082}"

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
    if [ "${VPN_SENTINEL_ALLOW_INSECURE:-false}" = "true" ]; then
      export CURL_OPTS="${CURL_OPTS:-} -k"
      log_warn "config" "⚠️ Insecure TLS mode enabled via VPN_SENTINEL_ALLOW_INSECURE=true; curl will not verify certificates"
    else
      export CURL_OPTS="${CURL_OPTS:-} -k"
      log_warn "config" "⚠️ No TLS certificate provided. To explicitly allow insecure TLS set VPN_SENTINEL_ALLOW_INSECURE=true, or mount a CA at VPN_SENTINEL_TLS_CERT_PATH"
    fi
  fi

  DEBUG="${VPN_SENTINEL_DEBUG:-false}"
  if [ "${DEBUG}" = "true" ]; then
    log_info "config" "🐛 Debug mode enabled - API responses will be logged"
    DEBUG_ENABLED=true
  else
    log_info "config" "ℹ️ Debug mode disabled"
    DEBUG_ENABLED=false
  fi
  export DEBUG_ENABLED

  GEOLOCATION_SERVICE="${VPN_SENTINEL_GEOLOCATION_SERVICE:-auto}"
}

validate_geolocation_service() {
  local service="$1"
  case "$service" in
    auto | ipinfo.io | ip-api.com)
      ;;
    *)
      log_error "config" "❌ Invalid VPN_SENTINEL_GEOLOCATION_SERVICE: $service"
      log_info "config" "📋 Valid options: auto, ipinfo.io, ip-api.com"
      log_info "config" "🔄 Defaulting to 'auto'"
      GEOLOCATION_SERVICE="auto"
      ;;
  esac
}
