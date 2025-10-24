#!/bin/sh
# Logging library for VPN Sentinel client
# Sourced by vpn-sentinel-client.sh

log_message() {
  local level="$1"
  local component="$2"
  local message="$3"
  local timestamp
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
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
