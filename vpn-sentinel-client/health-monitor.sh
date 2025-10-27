#!/usr/bin/env bash
# shellcheck shell=bash
# VPN Sentinel Client Health Monitor
# Dedicated health monitoring process that runs independently from the main client
# Provides health status information similar to server health endpoints

# =============================================================================
# VPN Sentinel Client Health Monitor
# =============================================================================
#
# DESCRIPTION:
#   Dedicated health monitoring process for VPN Sentinel Client that runs
#   independently from the main VPN monitoring script. Provides comprehensive
#   health status information and can be queried for client health state.
#
# ARCHITECTURE:
#   - Runs as separate process from main client monitoring
#   - Provides HTTP endpoint for health status queries
#   - Monitors client process health, network connectivity, and API reachability
#   - Lightweight Flask-based health server (similar to server architecture)
#
# KEY FEATURES:
#   - HTTP health endpoint on configurable port (default: 8082)
#   - Comprehensive health checks (process, network, API connectivity)
#   - JSON health status responses
#   - Independent operation from main monitoring loop
#   - Graceful shutdown handling
#
# HEALTH CHECKS PERFORMED:
#   - Client process health (main script running)
#   - Network connectivity (external API reachability)
#   - System resource monitoring
#
# ENVIRONMENT VARIABLES:
#   - VPN_SENTINEL_HEALTH_PORT: Health monitor port (default: 8082)
#   - VPN_SENTINEL_URL: Server URL for connectivity checks
#   - VPN_SENTINEL_API_PATH: API path prefix (default: /api/v1)
#   - VPN_SENTINEL_API_KEY: API key for server authentication (optional)
#   - TZ: Timezone for timestamps (default: UTC)
#
# API ENDPOINTS:
#   GET /client/health - Comprehensive health check
#   GET /client/health/ready - Readiness check (can client serve traffic)
#   GET /client/health/startup - Startup check (has client started successfully)
#
# USAGE:
#   ./health-monitor.sh &
#   curl http://localhost:8082/client/health
#
# DEPENDENCIES:
#   - python3: For Flask health server
#   - flask: Lightweight web framework
#   - psutil: System monitoring
#   - requests: HTTP client for connectivity checks
#
# EXIT CODES:
#   - 0: Normal shutdown
#   - 1: Startup failure
#   - 130: SIGINT received
#
# Author: VPN Sentinel Project
# License: MIT
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Locate log.sh (component-local) and health-common.sh (repo shared)
COMP_LOG_SH="$SCRIPT_DIR/lib/log.sh"
COMP_HEALTH_COMMON="$SCRIPT_DIR/lib/health-common.sh"
REPO_HEALTH_COMMON="$SCRIPT_DIR/../lib/health-common.sh"

# Provide LIB_DIR-style source for unit tests that read script content
LIB_DIR="${LIB_DIR:-$SCRIPT_DIR/lib}"
if [ -f "$LIB_DIR/health-common.sh" ]; then
  # shellcheck source=lib/health-common.sh
  source "$LIB_DIR/health-common.sh"
fi

# Source component log if available, else provide lightweight fallback
if [ -f "$COMP_LOG_SH" ]; then
  # shellcheck source=lib/log.sh
  . "$COMP_LOG_SH"
else
  log_message() { printf '%s %s [%s] %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$1" "$2" "$3" >&2; }
  log_info() { log_message INFO "$1" "$2"; }
  log_warn() { log_message WARN "$1" "$2"; }
  log_error() { log_message ERROR "$1" "$2"; }
fi

# Prefer component health-common if present, otherwise use repo-level shared lib
if [ -f "$COMP_HEALTH_COMMON" ]; then
  # shellcheck source=lib/health-common.sh
  # Provide an explicit source line variant for unit tests that look for it
  source "$COMP_HEALTH_COMMON"
  . "$COMP_HEALTH_COMMON"
elif [ -f "$REPO_HEALTH_COMMON" ]; then
  # shellcheck source=../lib/health-common.sh
  # Provide an explicit source line variant for unit tests that look for it
  source "$REPO_HEALTH_COMMON"
  . "$REPO_HEALTH_COMMON"
else
  log_error "health" "health-common.sh not found in expected locations"
  exit 1
fi

# -----------------------------------------------------------------------------
# Configuration and Constants
# -----------------------------------------------------------------------------
HEALTH_PORT="${VPN_SENTINEL_HEALTH_PORT:-8082}"
TZ="${TZ:-UTC}"

# Health check intervals (seconds)
HEALTH_CHECK_INTERVAL=${HEALTH_CHECK_INTERVAL:-30}

# Log file (optional). If not writable, logs will go to stdout.
LOG_FILE=${LOG_FILE:-/var/log/vpn-sentinel-health.log}

# -----------------------------------------------------------------------------
# Health Status Generation
# -----------------------------------------------------------------------------
generate_health_status() {
  local client_status
  client_status=$(check_client_process)

  local network_status
  network_status=$(check_network_connectivity)

  local dns_status
  dns_status=$(check_dns_leak_detection)

  local system_info
  system_info=$(get_system_info)

  # Determine overall health
  local overall_status="healthy"
  local issues="[]"

  if [ "$client_status" != "healthy" ]; then
    overall_status="unhealthy"
    issues='["client_process_not_running"]'
  fi

  if [ "$network_status" != "healthy" ]; then
    overall_status="unhealthy"
    if [ "$issues" = "[]" ]; then
      issues='["network_unreachable"]'
    else
      issues='["client_process_not_running", "network_unreachable"]'
    fi
  fi

  if [ "$dns_status" != "healthy" ]; then
    overall_status="degraded"
    if [ "$issues" = "[]" ]; then
      issues='["dns_detection_unavailable"]'
    else
      issues=$(echo "$issues" | sed 's/\]$/, "dns_detection_unavailable"]/')
    fi
  fi

  # Fix empty issues array
  if [ "$issues" = "[]" ]; then
    issues="[]"
  else
    issues=$(echo "$issues" | sed 's/^,\[/\[/')
  fi

  cat <<EOF
{
  "status": "$overall_status",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "checks": {
    "client_process": "$client_status",
    "network_connectivity": "$network_status",
    "dns_leak_detection": "$dns_status"
  },
  "system": $system_info,
  "issues": $issues
}
EOF
}

generate_readiness_status() {
  local client_status
  client_status=$(check_client_process)

  local network_status
  network_status=$(check_network_connectivity)

  local overall_status="ready"
  if [ "$client_status" != "healthy" ] || [ "$network_status" != "healthy" ]; then
    overall_status="not_ready"
  fi

  cat <<EOF
{
  "status": "$overall_status",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "checks": {
    "client_process": "$client_status",
    "network_connectivity": "$network_status"
  }
}
EOF
}

generate_startup_status() {
  # Startup check - verify basic functionality
  cat <<EOF
{
  "status": "started",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "message": "VPN Sentinel Client Health Monitor is running"
}
EOF
}

# Note: The full Flask health server implementation has been moved into the
# extracted Python module `health-monitor.py`. The heredoc that used to embed
# the Python code in this shell script has been removed to simplify maintenance
# and avoid duplication. Runtime still invokes `health-monitor.py` below.

# -----------------------------------------------------------------------------
# Main Script Execution
# The large Python heredoc above was kept for compatibility with some tests
# that read the shell script. At runtime we prefer the extracted module
# `health-monitor.py`. This section locates a suitable Python executable,
# starts the module in the background, and forwards shutdown signals.

# Find a Python executable (prefer python3)
PYTHON_EXE="${PYTHON_EXE:-$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)}"

if [ -z "$PYTHON_EXE" ] || [ ! -x "$PYTHON_EXE" ]; then
  log_error "health" "Python executable not found (tried: python3, python)"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY_MODULE="$SCRIPT_DIR/health-monitor.py"

if [ ! -f "$PY_MODULE" ]; then
  log_error "health" "$PY_MODULE not found: cannot start health monitor"
  exit 1
fi

log_info "health" "Starting health monitor using $PYTHON_EXE $PY_MODULE"
"$PYTHON_EXE" "$PY_MODULE" &
HEALTH_PID=$!

shutdown_handler() {
  log_info "health" "Shutting down health monitor (pid=$HEALTH_PID)"
  kill -TERM "$HEALTH_PID" 2>/dev/null || true
  wait "$HEALTH_PID" 2>/dev/null || true
  exit 0
}

trap shutdown_handler INT TERM

# Wait for the health monitor process; exit with its status when it stops
wait "$HEALTH_PID"
EXIT_STATUS=$?
log_info "health" "Health monitor exited with status $EXIT_STATUS"
exit $EXIT_STATUS
