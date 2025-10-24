#!/bin/bash
# Enhanced Health check script for VPN Sentinel Client
# Comprehensive health verification with detailed status reporting

# Source common health library
LIB_DIR="/app/lib"
# shellcheck source=lib/health-common.sh
. "$LIB_DIR/health-common.sh"

# Check if the main script is running
CLIENT_STATUS=$(check_client_process)
if [ "$CLIENT_STATUS" != "healthy" ]; then
    echo "❌ VPN Sentinel client script is not running"
    exit 1
fi

# Check if health monitor is running (if available)
HEALTH_MONITOR_RUNNING=false
if pgrep -f "health-monitor.sh" > /dev/null 2>&1; then
    HEALTH_MONITOR_RUNNING=true
fi

# Check if we can reach external services for DNS leak detection
NETWORK_STATUS=$(check_network_connectivity)
if [ "$NETWORK_STATUS" != "healthy" ]; then
    echo "❌ Cannot reach Cloudflare for DNS leak detection"
fi

# Check if we can reach the monitoring server (if URL is configured)
SERVER_WARNING=""
SERVER_STATUS=$(check_server_connectivity)
if [ "$SERVER_STATUS" = "unreachable" ]; then
    SERVER_WARNING="⚠️ Cannot reach VPN Sentinel server at $VPN_SENTINEL_URL (client will retry)"
fi

# Check health monitor endpoint (if running)
HEALTH_MONITOR_STATUS=""
if [ "$HEALTH_MONITOR_RUNNING" = true ]; then
    health_port="${VPN_SENTINEL_HEALTH_PORT:-8082}"
    if ! curl -f -s --max-time 5 "http://localhost:$health_port/health" > /dev/null 2>&1; then
        HEALTH_MONITOR_STATUS="⚠️ Health monitor running but not responding on port $health_port"
    else
        HEALTH_MONITOR_STATUS="✅ Health monitor responding on port $health_port"
    fi
fi

# Check system resources
MEMORY_WARNING=""
if command -v free > /dev/null 2>&1; then
    memory_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    if [ "$memory_usage" -gt 90 ]; then
        MEMORY_WARNING="⚠️ High memory usage: ${memory_usage}%"
    fi
fi

DISK_WARNING=""
if command -v df > /dev/null 2>&1; then
    disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$disk_usage" -gt 90 ]; then
        DISK_WARNING="⚠️ High disk usage: ${disk_usage}%"
    fi
fi

# Overall health assessment
OVERALL_HEALTHY=true
if [ "$NETWORK_STATUS" != "healthy" ]; then
    OVERALL_HEALTHY=false
fi

# Server connectivity is a warning, not a failure
# Memory/disk warnings don't fail the health check unless critical

# Report status
if [ "$OVERALL_HEALTHY" = true ]; then
    echo "✅ VPN Sentinel client is healthy"
else
    echo "❌ VPN Sentinel client has health issues"
    exit 1
fi

# Additional status information
if [ "$HEALTH_MONITOR_RUNNING" = true ]; then
    echo "✅ Health monitor is running"
else
    echo "ℹ️  Health monitor not running (optional)"
fi

if [ -n "$HEALTH_MONITOR_STATUS" ]; then
    echo "$HEALTH_MONITOR_STATUS"
fi

if [ -n "$SERVER_WARNING" ]; then
    echo "$SERVER_WARNING"
fi

if [ -n "$MEMORY_WARNING" ]; then
    echo "$MEMORY_WARNING"
fi

if [ -n "$DISK_WARNING" ]; then
    echo "$DISK_WARNING"
fi

# Provide JSON output if requested
if [ "${1:-}" = "--json" ]; then
    cat << EOF
{
  "status": "$([ "$OVERALL_HEALTHY" = true ] && echo "healthy" || echo "unhealthy")",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "checks": {
    "client_process": "$CLIENT_STATUS",
    "network_connectivity": "$NETWORK_STATUS",
    "server_connectivity": "$SERVER_STATUS",
    "health_monitor": "$([ "$HEALTH_MONITOR_RUNNING" = true ] && echo "running" || echo "not_running")"
  },
  "warnings": [
$(if [ -n "$SERVER_WARNING" ]; then echo "    \"server_unreachable\","; fi)
$(if [ -n "$MEMORY_WARNING" ]; then echo "    \"high_memory_usage\","; fi)
$(if [ -n "$DISK_WARNING" ]; then echo "    \"high_disk_usage\""; fi)
  ]
}
EOF
fi

exit 0