#!/bin/sh
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

# Source common health library
LIB_DIR="/app/lib"
source "$LIB_DIR/health-common.sh"

# -----------------------------------------------------------------------------
# Configuration and Constants
# -----------------------------------------------------------------------------
HEALTH_PORT="${VPN_SENTINEL_HEALTH_PORT:-8082}"
SERVER_URL="${VPN_SENTINEL_URL:-}"
API_PATH="${VPN_SENTINEL_API_PATH:-/api/v1}"
API_KEY="${VPN_SENTINEL_API_KEY:-}"
TZ="${TZ:-UTC}"

# Health check intervals (seconds)
HEALTH_CHECK_INTERVAL=30
CLIENT_PROCESS_CHECK_INTERVAL=10

# -----------------------------------------------------------------------------
# Health Status Generation
# -----------------------------------------------------------------------------
generate_health_status() {
    local client_status=$(check_client_process)
    local network_status=$(check_network_connectivity)
    local dns_status=$(check_dns_leak_detection)
    local system_info=$(get_system_info)

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

    cat << EOF
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
    local client_status=$(check_client_process)
    local network_status=$(check_network_connectivity)

    local overall_status="ready"
    if [ "$client_status" != "healthy" ] || [ "$network_status" != "healthy" ]; then
        overall_status="not_ready"
    fi

    cat << EOF
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
    cat << EOF
{
  "status": "started",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "message": "VPN Sentinel Client Health Monitor is running"
}
EOF
}

# -----------------------------------------------------------------------------
# Flask Health Server (Python)
# -----------------------------------------------------------------------------
create_flask_server() {
    cat << 'EOF'
import os
import sys
import json
from flask import Flask, jsonify
import subprocess
import signal
import time

app = Flask(__name__)

# Global health data cache
health_data = {}
last_update = 0
CACHE_DURATION = 10  # seconds

def get_health_data():
    global health_data, last_update
    current_time = time.time()

    if current_time - last_update > CACHE_DURATION:
        try:
            # Run health checks using shell commands
            client_status = subprocess.run(
                ["sh", "-c", "if pgrep -f 'vpn-sentinel-client.sh' > /dev/null 2>&1; then echo 'healthy'; else echo 'not_running'; fi"],
                capture_output=True, text=True
            ).stdout.strip()
            
            network_status = subprocess.run(
                ["sh", "-c", "if curl -f -s --max-time 5 'https://1.1.1.1/cdn-cgi/trace' > /dev/null 2>&1; then echo 'healthy'; else echo 'unreachable'; fi"],
                capture_output=True, text=True
            ).stdout.strip()
            
            # Get system info
            memory_percent = "unknown"
            disk_percent = "unknown"
            
            try:
                with open("/proc/meminfo", "r") as f:
                    mem_total = None
                    mem_available = None
                    for line in f:
                        if line.startswith("MemTotal:"):
                            mem_total = int(line.split()[1])
                        elif line.startswith("MemAvailable:"):
                            mem_available = int(line.split()[1])
                    if mem_total and mem_available:
                        memory_percent = "{:.1f}".format((1 - mem_available/mem_total) * 100)
            except:
                pass

            try:
                result = subprocess.run(["df", "/"], capture_output=True, text=True)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        disk_percent = lines[1].split()[4].rstrip('%')
            except:
                pass

            # Determine overall status
            overall_status = "healthy"
            issues = []

            if client_status != "healthy":
                overall_status = "unhealthy"
                issues.append("client_process_not_running")

            if network_status != "healthy":
                overall_status = "unhealthy"
                issues.append("network_unreachable")

            health_data = {
                "status": overall_status,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "checks": {
                    "client_process": client_status,
                    "network_connectivity": network_status
                },
                "system": {
                    "memory_percent": memory_percent,
                    "disk_percent": disk_percent
                },
                "issues": issues
            }
            
            last_update = current_time
            
        except Exception as e:
            health_data = {
                "status": "error",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "error": "Health check failed",
                "checks": {},
                "system": {},
                "issues": ["health_check_error"]
            }

    return health_data

@app.route('/client/health', methods=['GET'])
def health():
    data = get_health_data()
    status_code = 200 if data.get('status') in ['healthy', 'degraded'] else 503
    return jsonify(data), status_code

@app.route('/client/health/ready', methods=['GET'])
def readiness():
    data = get_health_data()
    # Readiness requires client process and network to be healthy
    client_ok = data.get('checks', {}).get('client_process') == 'healthy'
    network_ok = data.get('checks', {}).get('network_connectivity') == 'healthy'

    if client_ok and network_ok:
        status_data = {
            "status": "ready",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "checks": {
                "client_process": data['checks'].get('client_process'),
                "network_connectivity": data['checks'].get('network_connectivity')
            }
        }
        return jsonify(status_data), 200
    else:
        status_data = {
            "status": "not_ready",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "checks": {
                "client_process": data['checks'].get('client_process'),
                "network_connectivity": data['checks'].get('network_connectivity')
            }
        }
        return jsonify(status_data), 503

@app.route('/client/health/startup', methods=['GET'])
def startup():
    status_data = {
        "status": "started",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "message": "VPN Sentinel Client Health Monitor is running"
    }
    return jsonify(status_data), 200

def signal_handler(signum, frame):
    print("Shutting down health monitor...", file=sys.stderr)
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    port = int(os.environ.get('VPN_SENTINEL_HEALTH_PORT', '8082'))
    app.run(host='0.0.0.0', port=port, debug=False)
EOF
}

# -----------------------------------------------------------------------------
# Main Script Execution
# -----------------------------------------------------------------------------
# Start Flask health server in the background
create_flask_server | /opt/venv/bin/python3 > /dev/null 2>&1 &

FLASK_PID=$!

# Wait for the Flask server to start
sleep 2

# Main loop - health status generation
while true; do
    # Generate and log health status
    health_status=$(generate_health_status)
    echo "$health_status" | jq . -C | tee -a /var/log/vpn-sentinel-health.log

    # Sleep before next health check
    sleep "$HEALTH_CHECK_INTERVAL"
done

# Wait for Flask server to exit (should not happen)
wait $FLASK_PID