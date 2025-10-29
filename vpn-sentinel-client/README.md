# VPN Sentinel Client

This folder contains the VPN Sentinel client script `vpn-sentinel-client.sh`: a lightweight Docker-friendly monitor that runs in the VPN network namespace and periodically sends keepalive reports to a central monitoring server. It also performs DNS leak detection and gathers geolocation/provider information.

## What it does
- Periodically (default every 5 minutes) gathers public IP, geolocation and DNS resolver info
- Detects potential DNS leaks by comparing DNS resolver location to VPN exit node location
- Sends structured JSON keepalive payloads to the monitoring server (`/keepalive`)
- Optionally spawns a background health monitor process (`health-monitor.sh`) that exposes container health
- Uses secure HTTPS when configured with custom TLS certificates
- Structured, component-prefixed logging for easy filtering

## How it works (high level)
 - Uses external services to determine VPN exit IP and location (primary: `ipinfo.io`, fallback: `ip-api.com`, tertiary: `ipwhois.app`)
- Uses Cloudflare trace endpoint (`https://1.1.1.1/cdn-cgi/trace`) to determine DNS resolver location and data center (colo)
- Builds a JSON payload containing client id, timestamp, public IP, location and dns_test result and POSTs to `${SERVER_URL}/keepalive`
- Continues running indefinitely; resilient to transient API failures and network errors

## Files in this folder
- `vpn-sentinel-client.sh` — main client script (entrypoint for the client image)
- `health-monitor.sh` — optional helper (the script looks for `./health-monitor.sh` and starts it if present)

## Usage
Run the client container in the same network namespace as your VPN container. Example (host Docker run):

```bash
# run from repository root
docker run --rm --network container:vpn-container \
  -e VPN_SENTINEL_URL=http://your-server:5000 \
  -e VPN_SENTINEL_API_KEY=your-api-key \
  agigante80/vpn-sentinel-client:latest
```

Inside the project's test/deploy setups, the container is started with environment variables provided by the compose files.

## Environment variables
Below are the variables `vpn-sentinel-client.sh` reads or depends on (required vs optional and default shown):

- VPN_SENTINEL_URL (required)
  - Description: Base URL of the monitoring server (scheme + host + optional port)
  - Example: `https://vpn-monitor.example.com` or `http://host:5000`
  - Behavior when empty/unset: If `VPN_SENTINEL_URL` is not provided or is empty the client uses an internal default API base during startup (see `lib/config.sh` where `API_BASE_URL` is set from `VPN_SENTINEL_URL` with a fallback). Practically this means:
    - The client will still construct a `SERVER_URL` at runtime so the process keeps running.
    - Health and server-connectivity checks treat an empty `VPN_SENTINEL_URL` as "not_configured" (see `check_server_connectivity()` in `lib/health-common.sh`). That function returns `not_configured` instead of failing connectivity when the variable is empty.
    - Recommendation: set `VPN_SENTINEL_URL` in production so server-connectivity checks are meaningful and no ambiguous defaults are used.

- VPN_SENTINEL_API_PATH (optional)
  - Description: API path prefix appended to the base URL
  - Default: `/api/v1`

- VPN_SENTINEL_CLIENT_ID (optional)
  - Description: Unique client identifier (kebab-case). If not provided, a random id is generated at startup.
  - Example: `office-vpn-primary`

- VPN_SENTINEL_API_KEY (optional)
  - Description: Bearer token used to authenticate POSTs to the monitoring server

- VPN_SENTINEL_TLS_CERT_PATH (optional)
  - Description: Path to a custom TLS CA bundle inside the container; if provided, it is used for HTTPS verification
  - Behavior: If set and file missing, the script exits with an error. If not set, the script sets curl to trust self-signed certs (insecure) and logs a warning.

- VPN_SENTINEL_DEBUG (optional)
  - Description: If set to `true`, the script logs raw API responses and enables verbose debug logging
  - Default: `false`

 - VPN_SENTINEL_GEOLOCATION_SERVICE (optional)
  - Description: Forces which geolocation service to use: `auto`, `ipinfo.io`, `ip-api.com`, or `ipwhois.app`
  - Default: `auto`
  - Behavior:
    - `auto`: the client will try providers in order (ipinfo.io -> ip-api.com -> ipwhois.app). Each provider failure is logged (info/warn). If all providers fail an explicit error is logged indicating geolocation lookup failure.
    - `<provider>` (e.g., `ipinfo.io`): forces the client to query only that provider. In forced mode the client will not attempt fallbacks; failures are logged explicitly. Use forced mode for deterministic behavior or when you only trust a single provider.

- VPN_SENTINEL_HEALTH_MONITOR (optional)
  - Description: Enable/disable the dedicated health monitor background process
  - Default: `true` (starts `health-monitor.sh` if present)

- VPN_SENTINEL_HEALTH_PORT (optional)
  - Description: Port the health monitor binds to when enabled
  - Default: `8082`

Other script-level defaults (not read from env by the script but shown for awareness):

- TIMEOUT: HTTP max time for external calls and server POSTs — default `30` seconds
- INTERVAL: main keepalive interval — default `300` seconds (5 minutes)

Note: The script stores selected values in runtime variables (for example it constructs `SERVER_URL` by concatenating `VPN_SENTINEL_URL` + `VPN_SENTINEL_API_PATH`). If you need a different `INTERVAL` or `TIMEOUT`, update the script or wrap it in a small wrapper that modifies the variables before executing the main script.

## Health monitor

The client can optionally spawn a dedicated health monitor process (`health-monitor.sh`) that exposes lightweight HTTP endpoints for liveness/readiness and detailed JSON health status. The monitor is intended for container orchestrators and local debugging.

### Health monitor (deep dive)

Overview
- The health monitor runs as a separate process and provides an HTTP server (default port `8082`) with several endpoints that mirror common service health semantics. It aggregates checks from `lib/health-common.sh` (process, network, DNS probe, and system resource checks) and returns machine-readable JSON.

Endpoints
- `GET /client/health` — full health report (200 for healthy/degraded, 503 for unhealthy).
- `GET /client/health/ready` — readiness probe (200 when the client process and network are available; 503 otherwise).
- `GET /client/health/startup` — simple startup/status check (reports that the monitor is running).

Health check helper (`healthcheck.sh`)
 - The repository includes a lightweight helper script `healthcheck.sh` (in the client folder). It's a quick CLI probe that sources `lib/health-common.sh` and runs the same checks used by the monitor. Key facts:
   - Runs checks: client process presence, network connectivity (Cloudflare probe), server connectivity (uses `VPN_SENTINEL_URL`), and optional health-monitor HTTP probe.
   - Emits human-readable logs and can produce JSON when called with `--json`.
   - Returns non-zero exit code when the overall health is unhealthy (suitable for CI or container health probes).
   - When `VPN_SENTINEL_URL` is unset/empty `check_server_connectivity()` will report `not_configured` rather than failing.

Usage examples:

```bash
# Human-readable check
./healthcheck.sh

# JSON output for automation
./healthcheck.sh --json
```

JSON schema (summary)
- status: `healthy`, `degraded`, or `unhealthy`.
- timestamp: ISO8601 UTC timestamp.
- checks: object with `client_process`, `network_connectivity`, `dns_leak_detection` (values: `healthy`, `not_running`, `unreachable`, `unavailable`).
- system: object with `memory_percent` and `disk_percent` (may be `"unknown"` on minimal systems).
- issues: array of short issue codes (example: `"client_process_not_running"`, `"network_unreachable"`).

Example (curl):

```bash
# Full health
curl -sS http://localhost:8082/client/health | jq .

# Readiness
curl -sS -w "\nHTTP_STATUS:%{http_code}\n" http://localhost:8082/client/health/ready
```

Runtime & dependencies
- The health monitor ships an embedded Flask server (Python) in `health-monitor.sh` and prefers a venv Python at `/opt/venv/bin/python3` if present. The `vpn-sentinel-client` Docker image installs `python3`, `flask`, and `jq` so the full feature set is available in-container.
- If Python is not available locally, the monitor will not start; the client will still function without the monitor when `VPN_SENTINEL_HEALTH_MONITOR=false`.

Configuration (environment variables)
- `VPN_SENTINEL_HEALTH_PORT` (default `8082`) — port the monitor binds to.
- `VPN_SENTINEL_HEALTH_MONITOR` (default `true`) — whether the client spawns the monitor.
- `HEALTH_CHECK_INTERVAL` (default `30`) — seconds between health polling/log writes inside the monitor loop.
- `LOG_FILE` (optional) — path to write JSON status logs; falls back to stdout when unwritable.

Logging
- The monitor emits structured JSON health snapshots periodically (every `HEALTH_CHECK_INTERVAL` seconds). When `jq` is available the monitor pretty-prints JSON; otherwise compact JSON is emitted. Logs are written to `LOG_FILE` when writable or to stdout.

Security and stability notes
- The monitor performs outbound network probes to check connectivity. In restricted environments these probes may fail and cause `network_unreachable` issues in the health report — this is expected and reported as a warning/issue.
- Avoid exposing the health endpoint publicly without network-level protections. If you require authentication for the health endpoints, wrap the monitor behind a reverse proxy with ACLs or add token checks to the Flask app.

Testing and troubleshooting
- To test the monitor quickly inside the repository (no build):

```bash
# start the monitor in foreground
VPN_SENTINEL_HEALTH_PORT=8082 ./health-monitor.sh
# then query endpoints with curl from another shell
curl http://localhost:8082/client/health
```

- Common failure modes:
  - "client_process_not_running": the main `vpn-sentinel-client.sh` process is not running; start the client container or ensure the entrypoint is active.
  - "network_unreachable": external probes (Cloudflare/ipinfo) are blocked; verify container network and DNS.
  - Permission errors writing `LOG_FILE`: switch to stdout or point `LOG_FILE` to a writable path.

Integration with orchestrators
- Use `GET /client/health` for liveness checks and `GET /client/health/ready` for readiness probes. Example Kubernetes probes:

```yaml
livenessProbe:
  httpGet:
    path: /client/health
    port: 8082
  initialDelaySeconds: 10
  periodSeconds: 30
readinessProbe:
  httpGet:
    path: /client/health/ready
    port: 8082
  initialDelaySeconds: 5
  periodSeconds: 15
```

Notes
- The health monitor is optional; the primary client remains stateless and continues to send keepalives even if the monitor is disabled. The monitor's checks are intentionally lightweight to avoid impacting container resources.

## Testing & debugging
- To simulate a DNS leak for testing, the script includes commented lines in the DNS section where you can force `DNS_LOC` and `DNS_COLO` values — uncomment those during local testing to verify detection and notification workflows.
- Set `VPN_SENTINEL_DEBUG=true` to log raw API responses and aid troubleshooting.

## Logging
- Logs are written to stdout and follow the format:

```
[TIMESTAMP] LEVEL [COMPONENT] MESSAGE
```

Components used: `config`, `client`, `vpn-info`, `dns-test`, `api`.

## Troubleshooting
- If keepalives are not reaching the server:
  - Verify `VPN_SENTINEL_URL` and `VPN_SENTINEL_API_KEY` (if used)
  - Ensure the container shares the VPN network namespace and has external connectivity
  - Check TLS cert path and set `VPN_SENTINEL_TLS_CERT_PATH` if using custom CA
- If DNS leak detection seems incorrect:
  - Check connectivity to `ipinfo.io`, `ip-api.com` and `1.1.1.1` from inside the container
  - Use `VPN_SENTINEL_DEBUG=true` to inspect raw responses

## Contributing
- Keep this README in sync with changes to `vpn-sentinel-client.sh`.
- If you add environment variables or change defaults, update this file accordingly.

## License
- MIT
