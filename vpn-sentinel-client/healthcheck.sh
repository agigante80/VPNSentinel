#!/usr/bin/env bash
# shellcheck shell=bash
# Lightweight refactor: dynamic LIB_DIR, use health-common logging, robust JSON
# shellcheck disable=SC2155
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Prefer an explicitly provided LIB_DIR, otherwise use local layout or repo layout
LIB_DIR="${LIB_DIR:-$SCRIPT_DIR/lib}"
if [ ! -f "$LIB_DIR/health-common.sh" ] && [ -f "$SCRIPT_DIR/../lib/health-common.sh" ]; then
  LIB_DIR="$SCRIPT_DIR/../lib"
fi
#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC1091,SC1090
# shellcheck source=lib/health-common.sh
# Provide a 'source' line variant for unit tests that look for it
source "$LIB_DIR/health-common.sh"
. "$LIB_DIR/health-common.sh"

check_and_report() {
  # Check client
  CLIENT_STATUS=$(check_client_process)
  if [ "$CLIENT_STATUS" != "healthy" ]; then
    log_error "health" "❌ VPN Sentinel client script is not running"
    exit 1
  fi

  # Health monitor running check
  HEALTH_MONITOR_RUNNING=false
  if pgrep -f "health-monitor.sh" >/dev/null 2>&1; then
    HEALTH_MONITOR_RUNNING=true
  fi

  # Network and server checks
  NETWORK_STATUS=$(check_network_connectivity)
  SERVER_STATUS=$(check_server_connectivity)
  SERVER_WARNING=""
  if [ "$SERVER_STATUS" = "unreachable" ]; then
    SERVER_WARNING="server_unreachable"
    log_warn "health" "Cannot reach VPN Sentinel server at ${VPN_SENTINEL_URL:-(not set)}"
  fi

  # Helpful error message used in unit tests
  if [ "$NETWORK_STATUS" != "healthy" ]; then
    # Unit tests expect this exact message
    log_error "health" "❌ Cannot reach Cloudflare"
  fi

  # Health monitor endpoint probe
  HEALTH_MONITOR_STATUS=""
  if [ "$HEALTH_MONITOR_RUNNING" = true ]; then
    health_port="${VPN_SENTINEL_HEALTH_PORT:-8082}"
    if ! curl -f -s --max-time 5 "http://localhost:$health_port/health" >/dev/null 2>&1; then
      HEALTH_MONITOR_STATUS="monitor_not_responding"
      log_warn "health" "Health monitor running but not responding on port $health_port"
    else
      HEALTH_MONITOR_STATUS="monitor_ok"
      log_info "health" "Health monitor responding on port $health_port"
    fi
  fi

  # System resource checks
  WARNINGS=""
  if command -v free >/dev/null 2>&1; then
    memory_usage=$(free | awk 'NR==2{printf "%d", $3/$2*100}')
    if [ -n "$memory_usage" ] && [ "$memory_usage" -gt 90 ]; then
      WARNINGS="$WARNINGS
high_memory_usage"
      log_warn "health" "High memory usage: ${memory_usage}%"
    fi
  fi

  if command -v df >/dev/null 2>&1; then
    disk_usage=$(df / --output=pcent 2>/dev/null | tail -1 | tr -d ' %')
    if [ -n "$disk_usage" ] && [ "$disk_usage" -gt 90 ]; then
      WARNINGS="$WARNINGS
high_disk_usage"
      log_warn "health" "High disk usage: ${disk_usage}%"
    fi
  fi

  # Aggregate warnings
  [ -n "$SERVER_WARNING" ] && WARNINGS="$WARNINGS
$SERVER_WARNING"

  # Determine overall health (network failure is considered unhealthy)
  OVERALL_HEALTHY=true
  if [ "$NETWORK_STATUS" != "healthy" ]; then
    OVERALL_HEALTHY=false
    log_error "health" "Network connectivity issues detected"
  fi

  # Output human-readable summary
  if [ "$OVERALL_HEALTHY" = true ]; then
    log_info "health" "✅ VPN Sentinel client is healthy"
  else
    log_error "health" "VPN Sentinel client has health issues"
  fi

  if [ "$HEALTH_MONITOR_RUNNING" = true ]; then
    log_info "health" "Health monitor: running"
  else
    log_info "health" "Health monitor: not running (optional)"
  fi

  [ -n "$HEALTH_MONITOR_STATUS" ] && log_info "health" "Health monitor status: $HEALTH_MONITOR_STATUS"
  [ -n "$SERVER_WARNING" ] && log_warn "health" "Server connectivity warning"
  [ -n "$WARNINGS" ] && log_warn "health" "Warnings:$(printf '%s' "$WARNINGS")"

  # If requested, print JSON output
  if [ "${1:-}" = "--json" ]; then
    print_json "$OVERALL_HEALTHY" "$CLIENT_STATUS" "$NETWORK_STATUS" "$SERVER_STATUS" "$HEALTH_MONITOR_RUNNING" "$WARNINGS"
  fi

  # Exit non-zero if unhealthy
  [ "$OVERALL_HEALTHY" = true ] || exit 1
}

print_json() {
  status_bool="$1"
  client_status="$2"
  network_status="$3"
  server_status="$4"
  monitor_running="$5"
  warnings_blob="$6"

  status_val="$( [ "$status_bool" = true ] && echo "healthy" || echo "unhealthy" )"
  timestamp_val="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

  # Build warnings JSON array (safe, no trailing commas)
  if command -v jq >/dev/null 2>&1; then
    # convert newline-separated warnings into jq array
    warnings_json=$(printf '%s' "$warnings_blob" | sed '1d' | jq -R -s -c 'split("\n")[:-1]')
    jq -n \
      --arg status "$status_val" \
      --arg timestamp "$timestamp_val" \
      --arg client "$client_status" \
      --arg network "$network_status" \
      --arg server "$server_status" \
      --arg monitor "$( [ "$monitor_running" = true ] && echo running || echo not_running )" \
      --argjson warnings "$warnings_json" \
      '{status:$status, timestamp:$timestamp, checks:{client_process:$client, network_connectivity:$network, server_connectivity:$server, health_monitor:$monitor}, warnings:$warnings}'
  else
    # fallback: assemble JSON manually
    warnings_json="[]"
    if [ -n "$warnings_blob" ]; then
      # strip leading newline if present and build comma-separated list
      warnings_list=$(printf '%s' "$warnings_blob" | sed '1d' | awk 'NF' | sed -e 's/"/\\"/g' -e 's/.*/"&"/' | paste -sd, -)
      [ -n "$warnings_list" ] && warnings_json="[$warnings_list]"
    fi
    cat <<EOF
{
  "status": "$status_val",
  "timestamp": "$timestamp_val",
  "checks": {
    "client_process": "$client_status",
    "network_connectivity": "$network_status",
    "server_connectivity": "$server_status",
    "health_monitor": "$( [ "$monitor_running" = true ] && echo running || echo not_running )"
  },
  "warnings": $warnings_json
}
EOF
  fi
}

check_and_report "$1"

exit 0
