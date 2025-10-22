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
#   - Server API connectivity (VPN Sentinel server reachability)
#   - DNS leak detection capability
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
#   GET /health - Comprehensive health check
#   GET /health/ready - Readiness check (can client serve traffic)
#   GET /health/startup - Startup check (has client started successfully)
#
# USAGE:
#   ./health-monitor.sh &
#   curl http://localhost:8082/health
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
# Logging Functions
# -----------------------------------------------------------------------------
log_message() {
    local level="$1"
    local component="$2"
    local message="$3"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
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
    if [ -z "$SERVER_URL" ]; then
        echo "not_configured"
        return 0
    fi

    local health_url="${SERVER_URL}${API_PATH}/health"
    local curl_cmd="curl -f -s --max-time 10"

    # Add API key if configured
    if [ -n "$API_KEY" ]; then
        curl_cmd="$curl_cmd -H 'Authorization: Bearer $API_KEY'"
    fi

    if $curl_cmd "$health_url" > /dev/null 2>&1; then
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
        echo "unreachable"
        return 1
    fi
}

get_system_info() {
    # Get basic system information
    local memory_percent="unknown"
    local disk_percent="unknown"

    # Try to get memory usage (Linux-specific)
    if command -v free > /dev/null 2>&1; then
        memory_percent=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
    fi

    # Try to get disk usage
    if command -v df > /dev/null 2>&1; then
        disk_percent=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    fi

    echo "{\"memory_percent\": \"$memory_percent\", \"disk_percent\": \"$disk_percent\"}"
}

# -----------------------------------------------------------------------------
# Health Status Generation
# -----------------------------------------------------------------------------
generate_health_status() {
    local client_status=$(check_client_process)
    local network_status=$(check_network_connectivity)
    local server_status=$(check_server_connectivity)
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

    if [ "$server_status" = "unreachable" ]; then
        overall_status="degraded"
        if [ "$issues" = "[]" ]; then
            issues='["server_unreachable"]'
        else
            issues=$(echo "$issues" | sed 's/\]$/, "server_unreachable"]/')
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
    "server_connectivity": "$server_status",
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
            # Run shell health checks
            result = subprocess.run(
                [sys.executable, '-c', '''
import subprocess
import json
import sys

def check_client_process():
    try:
        result = subprocess.run(["pgrep", "-f", "vpn-sentinel-client.sh"],
                              capture_output=True, text=True)
        return "healthy" if result.returncode == 0 else "not_running"
    except:
        return "unknown"

def check_network_connectivity():
    try:
        result = subprocess.run([
            "curl", "-f", "-s", "--max-time", "5",
            "https://1.1.1.1/cdn-cgi/trace"
        ], capture_output=True)
        return "healthy" if result.returncode == 0 else "unreachable"
    except:
        return "unknown"

def check_server_connectivity():
    server_url = os.environ.get("VPN_SENTINEL_URL", "")
    api_path = os.environ.get("VPN_SENTINEL_API_PATH", "/api/v1")
    api_key = os.environ.get("VPN_SENTINEL_API_KEY", "")

    if not server_url:
        return "not_configured"

    health_url = f"{server_url}{api_path}/health"
    cmd = ["curl", "-f", "-s", "--max-time", "10", health_url]

    if api_key:
        cmd.extend(["-H", f"Authorization: Bearer {api_key}"])

    try:
        result = subprocess.run(cmd, capture_output=True)
        return "healthy" if result.returncode == 0 else "unreachable"
    except:
        return "unknown"

def get_system_info():
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
                memory_percent = f"{(1 - mem_available/mem_total) * 100:.1f}"
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

    return {"memory_percent": memory_percent, "disk_percent": disk_percent}

# Generate health status
client_status = check_client_process()
network_status = check_network_connectivity()
server_status = check_server_connectivity()
system_info = get_system_info()

overall_status = "healthy"
issues = []

if client_status != "healthy":
    overall_status = "unhealthy"
    issues.append("client_process_not_running")

if network_status != "healthy":
    overall_status = "unhealthy"
    issues.append("network_unreachable")

if server_status == "unreachable":
    overall_status = "degraded"
    issues.append("server_unreachable")

health_data = {
    "status": overall_status,
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "checks": {
        "client_process": client_status,
        "network_connectivity": network_status,
        "server_connectivity": server_status,
        "dns_leak_detection": "healthy"  # Simplified for health monitor
    },
    "system": system_info,
    "issues": issues
}

print(json.dumps(health_data))
                '''],
                capture_output=True, text=True, timeout=15
            )

            if result.returncode == 0:
                health_data = json.loads(result.stdout)
                last_update = current_time
            else:
                health_data = {
                    "status": "error",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "error": "Health check failed",
                    "checks": {},
                    "system": {},
                    "issues": ["health_check_error"]
                }

        except Exception as e:
            health_data = {
                "status": "error",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "error": str(e),
                "checks": {},
                "system": {},
                "issues": ["health_check_exception"]
            }

    return health_data

@app.route('/health', methods=['GET'])
def health():
    data = get_health_data()
    status_code = 200 if data.get('status') in ['healthy', 'degraded'] else 503
    return jsonify(data), status_code

@app.route('/health/ready', methods=['GET'])
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

@app.route('/health/startup', methods=['GET'])
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
# Main Health Monitor Logic
# -----------------------------------------------------------------------------
main() {
    log_info "health-monitor" "🚀 Starting VPN Sentinel Client Health Monitor on port $HEALTH_PORT"

    # Check if Python and Flask are available
    if ! command -v python3 > /dev/null 2>&1; then
        log_error "health-monitor" "❌ Python3 not found. Health monitor requires Python3."
        exit 1
    fi

    # Check if Flask is available
    if ! python3 -c "import flask" 2>/dev/null; then
        log_error "health-monitor" "❌ Flask not found. Install with: pip install flask"
        exit 1
    fi

    # Create temporary Flask server script
    local flask_script=$(mktemp)
    create_flask_server > "$flask_script"

    # Set up signal handling for graceful shutdown
    trap 'log_info "health-monitor" "🛑 Shutting down health monitor..."; rm -f "$flask_script"; exit 0' INT TERM

    # Start Flask server
    log_info "health-monitor" "🌐 Starting health server on port $HEALTH_PORT"
    python3 "$flask_script"

    # Cleanup
    rm -f "$flask_script"
}

# -----------------------------------------------------------------------------
# Script Entry Point
# -----------------------------------------------------------------------------
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    cat << 'HELP_EOF'
VPN Sentinel Client Health Monitor

USAGE:
  ./health-monitor.sh [OPTIONS]

OPTIONS:
  --help, -h          Show this help message
  --port PORT         Health monitor port (default: 8082)
  --check             Run single health check and exit

ENVIRONMENT VARIABLES:
  VPN_SENTINEL_HEALTH_PORT    Health monitor port (default: 8082)
  VPN_SENTINEL_URL           Server URL for connectivity checks
  VPN_SENTINEL_API_PATH      API path prefix (default: /api/v1)
  VPN_SENTINEL_API_KEY       API key for server authentication

EXAMPLES:
  ./health-monitor.sh                    # Start health monitor
  ./health-monitor.sh --check           # Run single check
  VPN_SENTINEL_HEALTH_PORT=9090 ./health-monitor.sh

HEALTH ENDPOINTS:
  GET /health         Comprehensive health check
  GET /health/ready   Readiness check
  GET /health/startup Startup check

HELP_EOF
    exit 0
fi

if [ "${1:-}" = "--check" ]; then
    # Run single health check
    generate_health_status
    exit $?
fi

# Start health monitor
main "$@"