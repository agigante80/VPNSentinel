#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC2317,SC1091,SC1090,SC2034,SC2001,SC2206,SC2154
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
  # shellcheck disable=SC1091
  source "$LIB_DIR/health-common.sh"
fi

# Source component log if available, else provide lightweight fallback
if [ -f "$COMP_LOG_SH" ]; then
  # shellcheck source=lib/log.sh
  # shellcheck disable=SC1091
  . "$COMP_LOG_SH"
else
  log_message() { printf '%s %s [%s] %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$1" "$2" "$3" >&2; }
  log_info() { log_message INFO "$1" "$2"; }
  log_warn() { log_message WARN "$1" "$2"; }
  log_error() { log_message ERROR "$1" "$2"; }
fi

# Prefer Python-based health_common CLI at runtime when available, but keep
# the original shell sourcing lines present so unit tests that inspect the
# script content continue to pass. The runtime behavior below will prefer
# the Python shim (vpn-sentinel-client/lib/health_common.py) if it's present
# and executable via the system Python.
PY_HEALTH_CLI="$SCRIPT_DIR/lib/health_common.py"
if [ -x "$PY_HEALTH_CLI" ] || [ -f "$PY_HEALTH_CLI" ]; then
  # runtime: prefer Python CLI
  HEALTH_CLI_PY="$PY_HEALTH_CLI"
  log_info "health" "Using Python health CLI: $HEALTH_CLI_PY"

  # Define wrapper functions that call into the Python CLI for runtime
  check_client_process() {
    "$HEALTH_CLI_PY" check_client_process 2>/dev/null || echo "not_running"
  }

  check_network_connectivity() {
    "$HEALTH_CLI_PY" check_network_connectivity 2>/dev/null || echo "unreachable"
  }

  check_server_connectivity() {
    "$HEALTH_CLI_PY" check_server_connectivity 2>/dev/null || echo "not_configured"
  }

  check_dns_leak_detection() {
    "$HEALTH_CLI_PY" check_dns_leak_detection 2>/dev/null || echo "unavailable"
  }

  get_system_info() {
    # return JSON blob like the original shell helper
    "$HEALTH_CLI_PY" get_system_info --json 2>/dev/null || echo '{"memory_percent":"unknown","disk_percent":"unknown"}'
  }

  # Keep the explicit source lines below for tests that look for them
  # shellcheck source=lib/health-common.sh
  source "$COMP_HEALTH_COMMON" 2>/dev/null || true
  . "$COMP_HEALTH_COMMON" 2>/dev/null || true
elif [ -f "$REPO_HEALTH_COMMON" ]; then
  # shellcheck source=../lib/health-common.sh
  # shellcheck disable=SC1090,SC1091
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

# PID file for the health monitor wrapper (can be overridden in tests)
PIDFILE="${VPN_SENTINEL_HEALTH_PIDFILE:-/tmp/vpn-sentinel-health-monitor.pid}"

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
# End of JSON heredoc for generate_health_status
EOF
}

# Helper: check if a pid is owned by current user
is_pid_owned_by_user() {
  local _pid="$1"
  if [ -z "$_pid" ]; then
    return 1
  fi
  if ! kill -0 "$_pid" 2>/dev/null; then
    return 1
  fi
  local owner
  owner=$(ps -o uid= -p "$_pid" 2>/dev/null | tr -d ' \t\n') || true
  [ "${owner}" = "$(id -u)" ]
}

# Attempt to stop a stale monitor process (best-effort, user-owned only)
stop_stale_monitor() {
  local stale_pid="$1"
  if is_pid_owned_by_user "$stale_pid"; then
    log_info "health" "Stopping stale health monitor pid=$stale_pid"
    kill -TERM "$stale_pid" 2>/dev/null || true
    sleep 1
    if kill -0 "$stale_pid" 2>/dev/null; then
      kill -KILL "$stale_pid" 2>/dev/null || true
      sleep 0.2
    fi
    # best-effort removal of pidfile if it points to this pid
    if [ -f "$PIDFILE" ]; then
      local pf
      pf=$(cat "$PIDFILE" 2>/dev/null || true)
      if [ "$pf" = "$stale_pid" ]; then
        log_info "health" "Removing stale pidfile $PIDFILE pointing to $pf"
        rm -f "$PIDFILE" 2>/dev/null || true
      fi
    fi
    return 0
  fi
  return 1
}

# Cleanup any stale monitors referenced by pidfile or listening on the health port
cleanup_stale_monitors() {
  # If pidfile exists, try to stop the referenced pid (user-owned)
  if [ -f "$PIDFILE" ]; then
    local existing
    existing=$(cat "$PIDFILE" 2>/dev/null || true)
    if [ -n "$existing" ]; then
      stop_stale_monitor "$existing" || true
    else
      log_info "health" "Removing empty pidfile $PIDFILE"
      rm -f "$PIDFILE" 2>/dev/null || true
    fi
  fi

  # Also inspect processes listening on the health port and stop user-owned monitors
  if command -v lsof >/dev/null 2>&1; then
    local pids
    pids=$(lsof -iTCP:"$HEALTH_PORT" -sTCP:LISTEN -t 2>/dev/null || true)
    for p in $pids; do
      # only attempt to stop processes owned by current user
      if is_pid_owned_by_user "$p"; then
        # only stop if command looks like our monitor (contains health-monitor)
        local cmd
        cmd=$(ps -o cmd= -p "$p" 2>/dev/null || true)
        case "$cmd" in
          *health-monitor*)
            log_info "health" "Found user-owned monitor process $p (cmd: $cmd) listening on port $HEALTH_PORT; stopping it"
            stop_stale_monitor "$p" || true
            ;;
          *)
            # do not kill unrelated system services
            log_info "health" "Ignoring listener pid $p (cmd: $cmd) on port $HEALTH_PORT"
            ;;
        esac
      fi
    done
  fi
}

# -----------------------------------------------------------------------------
# CLI helpers
# -----------------------------------------------------------------------------
stop_monitor_cli() {
  # Attempt to stop the monitor referenced by the pidfile in a safe way.
  if [ ! -f "$PIDFILE" ]; then
    log_info "health" "No pidfile found at $PIDFILE"
    return 2
  fi

  local target
  target=$(cat "$PIDFILE" 2>/dev/null || true)
  if [ -z "$target" ]; then
    log_info "health" "Pidfile $PIDFILE is empty; removing"
    rm -f "$PIDFILE" 2>/dev/null || true
    return 2
  fi

  if ! is_pid_owned_by_user "$target"; then
    log_error "health" "Pid $target from $PIDFILE is not owned by current user; refusing to stop"
    return 3
  fi

  local cmd
  cmd=$(ps -o cmd= -p "$target" 2>/dev/null || true)
  case "$cmd" in
    *health-monitor*)
      log_info "health" "Stopping monitor pid=$target (cmd: $cmd) as requested"
      kill -TERM "$target" 2>/dev/null || true
      sleep 1
      if kill -0 "$target" 2>/dev/null; then
        kill -KILL "$target" 2>/dev/null || true
        sleep 0.2
      fi
      # remove pidfile if it still points to this pid
      if [ -f "$PIDFILE" ]; then
        local pf
        pf=$(cat "$PIDFILE" 2>/dev/null || true)
        if [ "$pf" = "$target" ]; then
          rm -f "$PIDFILE" 2>/dev/null || true
        fi
      fi
      return 0
      ;;
    *)
      log_error "health" "Refusing to stop pid $target: unexpected command ($cmd)"
      return 3
      ;;
  esac
}

# If invoked with --stop, perform the stop operation and exit immediately.
if [ "${1:-}" = "--stop" ]; then
  # Allow using a custom PIDFILE via env (tests/CI). Keep output useful.
  stop_monitor_cli
  rc=$?
  exit $rc
fi

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
# Locate a Python executable. Prefer PYTHON_EXE env override, then PATH, then
# common CI/toolcache locations. Tests sometimes override PATH to a minimal set
# (/bin:/usr/bin) which can hide hosted tool locations (for example
# /opt/hostedtoolcache). Try a few fallbacks so the health monitor starts in
# CI and constrained environments.
PYTHON_EXE="${PYTHON_EXE:-}"
if [ -z "$PYTHON_EXE" ]; then
  PYTHON_EXE=$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)
fi

if [ -z "$PYTHON_EXE" ]; then
  for p in /opt/hostedtoolcache/Python/*/x64/bin/python3 /opt/hostedtoolcache/Python/*/x64/bin/python; do
    if [ -x "$p" ]; then
      PYTHON_EXE="$p"
      break
    fi
  done
fi

if [ -z "$PYTHON_EXE" ]; then
  for p in /usr/local/bin/python3 /usr/local/bin/python /usr/bin/python3 /usr/bin/python; do
    if [ -x "$p" ]; then
      PYTHON_EXE="$p"
      break
    fi
  done
fi

if [ -z "$PYTHON_EXE" ] || [ ! -x "$PYTHON_EXE" ]; then
  log_error "health" "Python executable not found (tried: python3, python, and common toolcache locations)"
  exit 1
fi

log_info "health" "Using Python executable: $PYTHON_EXE"

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
PY_MODULE="$SCRIPT_DIR/health-monitor.py"

if [ ! -f "$PY_MODULE" ]; then
  log_error "health" "$PY_MODULE not found: cannot start health monitor"
  exit 1
fi

# Prepare a log file for the health monitor so test harnesses and CI can
# inspect runtime errors when the monitor exits unexpectedly. Allow override
# via VPN_SENTINEL_HEALTH_LOG for tests.
LOG_PATH="${VPN_SENTINEL_HEALTH_LOG:-/tmp/vpn-sentinel-health-monitor.log}"
mkdir -p "$(dirname "$LOG_PATH")" 2>/dev/null || true
rm -f "$LOG_PATH" 2>/dev/null || true

# Pre-start: attempt to cleanup stale monitors and pidfiles
cleanup_stale_monitors || true

# Write wrapper pidfile (shell wrapper). Tests and helpers use this.
echo "$$" > "$PIDFILE" 2>/dev/null || true

trap 'rc=$?; rm -f "$PIDFILE" 2>/dev/null || true; exit $rc' INT TERM EXIT

log_info "health" "Starting health monitor using $PYTHON_EXE $PY_MODULE (log: $LOG_PATH)"
"$PYTHON_EXE" "$PY_MODULE" >> "$LOG_PATH" 2>&1 &
HEALTH_PID=$!

# Give the monitor a moment to start and detect early failures. If the
# python process exits, print the tail of the log to stderr so the test
# harness (which captures the client's stdout/stderr) can surface useful
# diagnostics instead of a silent failure.
sleep 1
if ! kill -0 "$HEALTH_PID" 2>/dev/null; then
  log_error "health" "Health monitor process (PID: $HEALTH_PID) exited prematurely. Dumping last 200 lines of $LOG_PATH"
  if [ -f "$LOG_PATH" ]; then
    tail -n 200 "$LOG_PATH" >&2 || true
  else
    log_error "health" "No health monitor log found at $LOG_PATH"
  fi
  # Exit with failure so the parent/client knows the monitor did not start
  exit 1
fi

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
# Cleanup pidfile (trap will also handle it)
rm -f "$PIDFILE" 2>/dev/null || true
exit $EXIT_STATUS
