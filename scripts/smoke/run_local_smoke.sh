#!/usr/bin/env bash
set -euo pipefail

# Simple smoke test for local server+client (no VPN container)
# Steps:
# 1. Stop/remove previous containers/images related to vpn-sentinel
# 2. Build server and client images (tags: vpn-sentinel-server:local, vpn-sentinel-client:local)
# 3. Start server and client containers (briefly)
# 4. Assert the server received a keepalive from the client
# 5. Check client health endpoints (/client/health, /client/health/ready, /client/health/startup)
# 6. Check dashboard HTTP endpoint
# 7. Teardown containers

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../" && pwd)"
cd "$ROOT_DIR"

# Configurable values
# Default to localhost for local testing; allow override via env var
SERVER_HOST="${SERVER_HOST:-localhost}"
API_PORT=${API_PORT:-5000}
API_PATH=${API_PATH:-/api/v1}
SERVER_IMAGE=${SERVER_IMAGE:-vpn-sentinel-server:local}
CLIENT_IMAGE=${CLIENT_IMAGE:-vpn-sentinel-client:local}
SERVER_NAME=${SERVER_NAME:-vpn-sentinel-server-smoke}
CLIENT_NAME=${CLIENT_NAME:-vpn-sentinel-client-smoke}
CLIENT_ID=${CLIENT_ID:-smoke-client}
CLIENT_HEALTH_PORT=${CLIENT_HEALTH_PORT:-8082}
SERVER_DASHBOARD_PORT=${SERVER_DASHBOARD_PORT:-8080}
SERVER_HEALTH_PORT=${SERVER_HEALTH_PORT:-8081}

CERT_DIR="${CERT_DIR:-$ROOT_DIR/scripts/smoke/certs}"

# If running locally and SERVER_HOST is localhost, try detect Docker bridge gateway
# so containers can reach services published on the host. This prefers an explicit
# SERVER_HOST env override when provided.
if [ "${SERVER_HOST}" = "localhost" ] || [ "${SERVER_HOST}" = "127.0.0.1" ]; then
  # Attempt to detect Docker bridge gateway IP (common default 172.17.0.1)
  if command -v docker >/dev/null 2>&1; then
    DOCKER_GW=$(docker network inspect bridge --format '{{range .IPAM.Config}}{{.Gateway}}{{end}}' 2>/dev/null || true)
    if [ -n "${DOCKER_GW}" ]; then
      # Use simple echo here to avoid colliding with external 'info' command
      echo "[INFO] Detected Docker bridge gateway: ${DOCKER_GW} — using it for container-to-host access"
      SERVER_HOST="${DOCKER_GW}"
    fi
  fi
fi

info(){ echo "[INFO] $*"; }
err(){ echo "[ERROR] $*" >&2; }

## Timeouts
BUILD_TIMEOUT=300
START_TIMEOUT=30
RETRY_INTERVAL=2

info(){ echo "[INFO] $*"; }
err(){ echo "[ERROR] $*" >&2; }

cleanup_containers(){
  info "Stopping and removing containers (if any)"
  # Remove by explicit names
  docker rm -f "$CLIENT_NAME" >/dev/null 2>&1 || true
  docker rm -f "$SERVER_NAME" >/dev/null 2>&1 || true

  # Remove any other containers derived from the same images (old runs)
  for cid in $(docker ps -aq --filter "ancestor=${CLIENT_IMAGE}" --format '{{.ID}}' 2>/dev/null || true); do
    docker rm -f "$cid" >/dev/null 2>&1 || true
  done
  for cid in $(docker ps -aq --filter "ancestor=${SERVER_IMAGE}" --format '{{.ID}}' 2>/dev/null || true); do
    docker rm -f "$cid" >/dev/null 2>&1 || true
  done

  # Also remove any containers with names that include vpn-sentinel-client or vpn-sentinel-server
  for cid in $(docker ps -aq --filter "name=vpn-sentinel-client" --format '{{.ID}}' 2>/dev/null || true); do
    docker rm -f "$cid" >/dev/null 2>&1 || true
  done
  for cid in $(docker ps -aq --filter "name=vpn-sentinel-server" --format '{{.ID}}' 2>/dev/null || true); do
    docker rm -f "$cid" >/dev/null 2>&1 || true
  done
}

cleanup_images(){
  info "Removing local images (if present)"
  docker image rm -f "$CLIENT_IMAGE" >/dev/null 2>&1 || true
  docker image rm -f "$SERVER_IMAGE" >/dev/null 2>&1 || true
}

# Generate temporary self-signed certs for smoke testing
generate_self_signed_certs(){
  mkdir -p "$CERT_DIR"
  # Use openssl to generate a cert and key
  if ! command -v openssl >/dev/null 2>&1; then
    err "openssl not found; cannot generate self-signed certs"
    return 1
  fi
  info "Generating self-signed cert/key in ${CERT_DIR}"
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -subj "/CN=localhost" \
    -keyout "$CERT_DIR/key.pem" \
    -out "$CERT_DIR/cert.pem" >/dev/null 2>&1 || return 2
  chmod 644 "$CERT_DIR/cert.pem" || true
  chmod 644 "$CERT_DIR/key.pem" || true
  return 0
}

trap 'err "Interrupted; tearing down..."; cleanup_containers; exit 2' INT TERM

run_smoke_once(){
  # $1 -> FORCE_TLS: "auto" | "yes" | "no"
  local FORCE_TLS=${1:-auto}

  # Clean containers from any previous run
  cleanup_containers

  # Decide whether to enable TLS for this run
  local USE_TLS=0
  if [ "${FORCE_TLS}" = "yes" ]; then
    if [ -f "$CERT_DIR/cert.pem" ] && [ -f "$CERT_DIR/key.pem" ]; then
      USE_TLS=1
    else
      info "Requested TLS run but certs not found in ${CERT_DIR}; generating temporary self-signed certs"
      generate_self_signed_certs || {
        err "Failed to generate self-signed certs; skipping TLS run"
        return 0
      }
      USE_TLS=1
    fi
  elif [ "${FORCE_TLS}" = "no" ]; then
    USE_TLS=0
  else
    # auto: enable TLS only if certs exist
    if [ -f "$CERT_DIR/cert.pem" ] && [ -f "$CERT_DIR/key.pem" ]; then
      info "Found TLS certs in $CERT_DIR — enabling TLS for server"
      USE_TLS=1
    else
      USE_TLS=0
    fi
  fi

  if [ "$USE_TLS" -eq 1 ]; then
    # Ensure certs are readable by the container's non-root user
    chmod 644 "$CERT_DIR/cert.pem" || true
    chmod 644 "$CERT_DIR/key.pem" || true
    SERVER_TLS_CERT_PATH="/certs/cert.pem"
    SERVER_TLS_KEY_PATH="/certs/key.pem"
  fi

  # Prepare logging directory for this iteration
  TS=$(date -u +%Y%m%dT%H%M%SZ)
  ITER_NAME="${FORCE_TLS}"
  # Use workspace-relative log dir (avoid embedding absolute user paths)
  LOG_DIR="scripts/smoke/logs/${TS}_${ITER_NAME}"
  mkdir -p "$ROOT_DIR/$LOG_DIR"
  mkdir -p "$LOG_DIR"
  info "Starting server container (TLS=${USE_TLS}) -- logs -> ${ROOT_DIR}/${LOG_DIR}"
  SERVER_RUN_OPTS=( -d --name "$SERVER_NAME" -e VPN_SENTINEL_SERVER_API_PORT=$API_PORT -e VPN_SENTINEL_API_PATH=$API_PATH -e VPN_SENTINEL_API_KEY= -p ${API_PORT}:${API_PORT} -p ${SERVER_DASHBOARD_PORT}:${SERVER_DASHBOARD_PORT} -p ${SERVER_HEALTH_PORT}:${SERVER_HEALTH_PORT} )
  if [ "$USE_TLS" -eq 1 ]; then
    SERVER_RUN_OPTS+=( -v "$CERT_DIR":/certs:ro -e VPN_SENTINEL_TLS_CERT_PATH="$SERVER_TLS_CERT_PATH" -e VPN_SENTINEL_TLS_KEY_PATH="$SERVER_TLS_KEY_PATH" )
  fi

  # Start server and capture container ID
  SERVER_CID=$(docker run "${SERVER_RUN_OPTS[@]}" "$SERVER_IMAGE")
  # Normalize: docker run in detached mode prints container ID; if not, query by name
  SERVER_CID=${SERVER_CID:-$(docker ps -aq --filter "name=${SERVER_NAME}" --format '{{.ID}}' 2>/dev/null || true)}

  info "Waiting for server health endpoint to become available"
  if [ "$USE_TLS" -eq 1 ]; then
    PROTO="https"
  else
    PROTO="http"
  fi
  SERVER_URL="${PROTO}://${SERVER_HOST}:${API_PORT}${API_PATH}"
  SERVER_HEALTH_URL="${PROTO}://${SERVER_HOST}:${SERVER_HEALTH_PORT}/health"

  # Curl options: allow insecure if using self-signed TLS certs
  if [ "$USE_TLS" -eq 1 ]; then
    CURL_OPTS="-k"
  else
    CURL_OPTS=""
  fi
  server_up=1
  for i in $(seq 1 $START_TIMEOUT); do
    if curl ${CURL_OPTS} -s -f "${SERVER_HEALTH_URL}" >/dev/null 2>&1; then
      server_up=0; break
    fi
    sleep $RETRY_INTERVAL
  done
  if [ $server_up -ne 0 ]; then
    err "Server health endpoint did not become ready within ${START_TIMEOUT}s"
    docker logs "$SERVER_NAME" --tail 200 || true
    docker logs "$SERVER_NAME" > "$LOG_DIR/server_startup.log" 2>&1 || true
    cleanup_containers
    return 3
  fi
  info "Server API is up at ${SERVER_URL} (health: ${SERVER_HEALTH_URL})"
  # Capture initial server health response
  curl ${CURL_OPTS} -s -D - "${SERVER_HEALTH_URL}" > "$LOG_DIR/server_health_response.txt" 2>&1 || true

  info "Starting client container (health monitor enabled)"
  CLIENT_RUN_OPTS=( -d --name "$CLIENT_NAME" -e VPN_SENTINEL_URL="${PROTO}://${SERVER_HOST}:${API_PORT}" -e VPN_SENTINEL_API_PATH=$API_PATH -e VPN_SENTINEL_CLIENT_ID=$CLIENT_ID -e VPN_SENTINEL_API_KEY= -e VPN_SENTINEL_DEBUG=true -e VPN_SENTINEL_INTERVAL=3 -e VPN_SENTINEL_TIMEOUT=3 -e VPN_SENTINEL_HEALTH_MONITOR=true -p ${CLIENT_HEALTH_PORT}:${CLIENT_HEALTH_PORT} )
  if [ "$USE_TLS" -eq 1 ]; then
    # allow insecure for test client (self-signed) or you can mount CA instead
    CLIENT_RUN_OPTS+=( -e VPN_SENTINEL_ALLOW_INSECURE=true )
  fi
  # Start client and capture container ID
  CLIENT_CID=$(docker run "${CLIENT_RUN_OPTS[@]}" "$CLIENT_IMAGE")
  CLIENT_CID=${CLIENT_CID:-$(docker ps -aq --filter "name=${CLIENT_NAME}" --format '{{.ID}}' 2>/dev/null || true)}

  info "Waiting for client to send first keepalive"
  keepalive_received=1
  for i in $(seq 1 20); do
    sleep 1
    # Query server status and look for the client id
    if curl ${CURL_OPTS} -s "${SERVER_URL}/status" | grep -q "\"${CLIENT_ID}\""; then
      keepalive_received=0
      break
    fi
  done
  if [ $keepalive_received -ne 0 ]; then
    err "Server did not report keepalive from client '${CLIENT_ID}'"
    echo "--- Server logs ---"
    docker logs "$SERVER_NAME" --tail 200 || true
    docker logs "$SERVER_NAME" > "$LOG_DIR/server_logs.log" 2>&1 || true
    echo "--- Client logs ---"
    docker logs "$CLIENT_NAME" --tail 200 || true
    docker logs "$CLIENT_NAME" > "$LOG_DIR/client_logs.log" 2>&1 || true
    # Save last status response for debugging
    curl ${CURL_OPTS} -s "${SERVER_URL}/status" > "$LOG_DIR/status_response.json" || true
    cleanup_containers
    return 4
  fi
  info "Server received keepalive from '${CLIENT_ID}'"
  info "Checking client health endpoints (via host port ${CLIENT_HEALTH_PORT})"
  CLIENT_HEALTH_BASE="http://localhost:${CLIENT_HEALTH_PORT}/client"

  # Wait for client health base to become available (health monitor can be slow to bind)
  info "Waiting up to 10s for client health endpoint to respond"
  client_health_ready=1
  for i in $(seq 1 10); do
    if curl ${CURL_OPTS} -s -f "${CLIENT_HEALTH_BASE}/health" >/dev/null 2>&1; then
      client_health_ready=0
      break
    fi
    sleep 1
  done
  if [ $client_health_ready -ne 0 ]; then
    err "Client health endpoint did not become ready on host port ${CLIENT_HEALTH_PORT}"
    docker logs "$CLIENT_NAME" --tail 200 || true
    docker logs "$CLIENT_NAME" > "$LOG_DIR/client_logs.log" 2>&1 || true
    cleanup_containers
    return 5
  fi

  for ep in "health" "health/ready" "health/startup"; do
    info "Checking ${CLIENT_HEALTH_BASE}/${ep}"
    if ! curl ${CURL_OPTS} -s -f "${CLIENT_HEALTH_BASE}/${ep}" >/dev/null 2>&1; then
      err "Client health endpoint ${ep} failed"
      docker logs "$CLIENT_NAME" --tail 200 || true
      docker logs "$CLIENT_NAME" > "$LOG_DIR/client_logs.log" 2>&1 || true
      cleanup_containers
      return 5
    fi
  done
  info "Client health endpoints OK"

  if [ "$USE_TLS" -eq 1 ]; then
    DASH_PROTO="https"
  else
    DASH_PROTO="http"
  fi
  info "Checking dashboard at ${DASH_PROTO}://${SERVER_HOST}:${SERVER_DASHBOARD_PORT}/dashboard"
  DASH_URL1="${DASH_PROTO}://${SERVER_HOST}:${SERVER_DASHBOARD_PORT}/dashboard"
  DASH_URL2="${DASH_PROTO}://${SERVER_HOST}:${SERVER_DASHBOARD_PORT}/dashboard/"
  dash_ok=1
  for url in "$DASH_URL1" "$DASH_URL2"; do
    if curl ${CURL_OPTS} -s -f "$url" >/dev/null 2>&1; then
      dash_ok=0
      break
    fi
  done
  if [ $dash_ok -ne 0 ]; then
    err "Dashboard not reachable on ${SERVER_DASHBOARD_PORT}"
    docker logs "$SERVER_NAME" --tail 200 || true
    docker logs "$SERVER_NAME" > "$LOG_DIR/server_logs.log" 2>&1 || true
    # Save status and dashboard probe outputs
    curl ${CURL_OPTS} -s "${SERVER_URL}/status" > "$LOG_DIR/status_response.json" || true
    curl ${CURL_OPTS} -s "${DASH_URL1}" > "$LOG_DIR/dashboard_response.html" 2>&1 || true
    cleanup_containers
    return 6
  fi
  info "Dashboard reachable"
  # Save logs and probes for successful run as well
  docker logs "$SERVER_NAME" > "$LOG_DIR/server_logs.log" 2>&1 || true
  docker logs "$CLIENT_NAME" > "$LOG_DIR/client_logs.log" 2>&1 || true
  curl ${CURL_OPTS} -s "${SERVER_URL}/status" > "$LOG_DIR/status_response.json" || true
  curl ${CURL_OPTS} -s "${DASH_URL1}" > "$LOG_DIR/dashboard_response.html" 2>&1 || true

  info "Smoke test passed for TLS=${USE_TLS} — tearing down containers"
  # Write a small summary file into the log dir for debugging
  # Write a compact summary using workspace-relative log_dir to avoid embedding
  # absolute user home paths in generated artifacts.
  cat > "$ROOT_DIR/$LOG_DIR/smoke-summary.txt" <<EOF
timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)
server_image: ${SERVER_IMAGE}
client_image: ${CLIENT_IMAGE}
server_container: ${SERVER_CID:-unknown}
client_container: ${CLIENT_CID:-unknown}
tls_enabled: ${USE_TLS}
log_dir: ${LOG_DIR}
EOF

  cleanup_containers
  return 0

}


### Main: run twice (no-TLS first, then TLS)
info "1) Cleaning previous containers and images"
cleanup_containers
cleanup_images

info "2) Building server and client images"
docker build -t "$SERVER_IMAGE" -f vpn-sentinel-server/Dockerfile .
docker build -t "$CLIENT_IMAGE" -f vpn-sentinel-client/Dockerfile .

info "Running smoke: iteration 1 (no TLS)"
run_smoke_once no
rc1=$?

info "Running smoke: iteration 2 (with TLS if certs exist)"
run_smoke_once yes
rc2=$?

if [ $rc1 -ne 0 ]; then
  err "Smoke (no-TLS) failed with code $rc1"
fi
if [ $rc2 -ne 0 ]; then
  err "Smoke (TLS) failed or was skipped with code $rc2"
fi

if [ $rc1 -eq 0 ] && [ $rc2 -eq 0 ]; then
  info "Both smoke iterations passed"
  exit 0
fi

err "One or more smoke iterations failed";
exit 10
