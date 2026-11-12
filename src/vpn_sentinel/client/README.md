# VPN Sentinel Client

This folder contains the VPN Sentinel client, started with `python -m vpn_sentinel.client` (the entrypoint of the client image). It is a lightweight Docker-friendly monitor that runs in the VPN network namespace and periodically sends keepalive reports to a central monitoring server. It also performs DNS leak detection and gathers geolocation/provider information.

## What it does
- Periodically (default every 5 minutes) gathers public IP, geolocation and DNS resolver info
- Detects potential DNS leaks by comparing DNS resolver location to VPN exit node location
- Sends structured JSON keepalive payloads to the monitoring server (`POST <VPN_SENTINEL_URL><VPN_SENTINEL_API_PATH>/keepalive`, by default `/api/v1/keepalive`)
- Optionally spawns a background health monitor process that exposes container health
- Uses HTTPS verification with a custom CA bundle when `VPN_SENTINEL_TLS_CERT_PATH` is set
- Structured, component-prefixed logging for easy filtering

## How it works (high level)
- Uses external services to determine VPN exit IP and location (primary: `ipinfo.io`, fallback: `ip-api.com`, tertiary: `ipwhois.app`)
- Uses Cloudflare trace endpoint (`https://1.1.1.1/cdn-cgi/trace`) to determine DNS resolver location and data center (colo)
- Builds a JSON payload containing client id, timestamp, public IP, location and the DNS test result, and POSTs it to the server with the `X-API-Key` header when an API key is configured
- Continues running indefinitely; resilient to transient API failures and network errors

## Files in this folder
- `__main__.py`: the client (config loading, keepalive loop, health monitor supervision)
- `Dockerfile`: the client image (`CMD ["python", "-m", "vpn_sentinel.client"]`)

The shared logic (configuration, payload, geolocation, DNS parsing, health checks) lives in `src/vpn_sentinel/common/`. The health monitor scripts are in `src/vpn_sentinel/common/health_scripts/`.

## Usage
Run the client container in the same network namespace as your VPN container. Example (host Docker run):

```bash
# run from repository root
docker run --rm --network container:vpn-container \
  -e VPN_SENTINEL_URL=http://your-server:5000 \
  -e VPN_SENTINEL_API_KEY=your-api-key \
  agigante80/vpn-sentinel-client:latest
```

From a source checkout (after `pip install -e .`) run `python -m vpn_sentinel.client` with the same variables. Inside the project's test/deploy setups, the container is started with environment variables provided by the compose files.

## Environment variables
The client reads these variables (`src/vpn_sentinel/common/config.py` and `payload.py`, plus the client entry point):

- `VPN_SENTINEL_URL` (set it in production)
  - Description: Base URL of the monitoring server (scheme + host + optional port), without the API path
  - Example: `https://vpn-monitor.example.com` or `http://host:5000`
  - Default: `http://your-server-url:5000`, a placeholder. If you leave it unset the client keeps running but its keepalives go to a host that does not exist, so set it.

- `VPN_SENTINEL_API_PATH` (optional)
  - Description: API path prefix appended to the base URL; must match the server
  - Default: `/api/v1`

- `VPN_SENTINEL_CLIENT_ID` (optional)
  - Description: Unique client identifier (kebab-case; other characters are replaced by `-`). If not provided, `vpn-monitor-<12 random digits>` is generated at startup.
  - Example: `office-vpn-primary`

- `VPN_SENTINEL_API_KEY` or `VPN_SENTINEL_API_KEY_FILE` (must match the server)
  - Description: API key sent in the `X-API-Key` header. `VPN_SENTINEL_API_KEY_FILE` reads it from a file (Docker secret) instead.
  - Behavior: setting both, or pointing the `_FILE` variable at a missing, unreadable or empty file, makes the client exit with code 2 at startup.

- `VPN_SENTINEL_INTERVAL` (optional)
  - Description: Keepalive interval in seconds
  - Default: `300` (5 minutes)

- `VPN_SENTINEL_TIMEOUT` (optional)
  - Description: HTTP timeout in seconds for the server POST
  - Default: `30`

- `VPN_SENTINEL_TLS_CERT_PATH` (optional)
  - Description: Path to a custom CA bundle inside the container, used to verify the server certificate over HTTPS
  - Behavior: if the bundle cannot be loaded the client falls back to the system trust store.

- `VPN_SENTINEL_ALLOW_INSECURE` (optional)
  - Description: If `true`, TLS certificate verification is disabled (development only)
  - Default: `false`

- `VPN_SENTINEL_DEBUG` (optional)
  - Description: If `true`, enables verbose debug logging
  - Default: `false`

- `VPN_SENTINEL_GEOLOCATION_SERVICE` (optional)
  - Description: Forces which geolocation service to use: `auto`, `ipinfo.io`, `ip-api.com`, or `ipwhois.app`
  - Default: `auto`
  - Behavior:
    - `auto`: the client will try providers in order (ipinfo.io -> ip-api.com -> ipwhois.app). Each provider failure is logged. If all providers fail an explicit error is logged indicating geolocation lookup failure.
    - `<provider>` (e.g., `ipinfo.io`): forces the client to query only that provider, with no fallbacks. Use forced mode for deterministic behavior or when you only trust a single provider.

- `VPN_SENTINEL_HEALTH_MONITOR` (optional)
  - Description: Enable/disable the dedicated health monitor background process
  - Default: `true` (set `false` to disable)

- `VPN_SENTINEL_HEALTH_PORT` (optional)
  - Description: Port the health monitor binds to when enabled
  - Default: `8082`

- `VPN_SENTINEL_HEALTH_PIDFILE` (optional)
  - Description: PID file used by the health monitor wrapper
  - Default: `/tmp/vpn-sentinel-health-monitor.pid`

## Health monitor

The client spawns a dedicated health monitor process (`health_scripts/health_monitor_wrapper.py`) unless `VPN_SENTINEL_HEALTH_MONITOR=false`. It exposes lightweight HTTP endpoints for liveness/readiness and a JSON health status, intended for container orchestrators and local debugging.

Endpoints (default port `8082`)
- `GET /client/health`: full health report (200 for healthy/degraded, 503 for unhealthy).
- `GET /client/health/ready`: readiness probe (200 when the client process and network are available; 503 otherwise).
- `GET /client/health/startup`: simple startup/status check (reports that the monitor is running).

Health check helper (`healthcheck.py`)
- The image runs `python3 /app/healthcheck.py` as its Docker `HEALTHCHECK`. The same helper is in the common package and is a quick CLI probe:
  - Checks client process presence, network connectivity (Cloudflare probe), DNS leak detection, the health monitor process and system resources. Server connectivity is reported as `not_checked`, because successful keepalives already prove it.
  - Emits human-readable logs, or JSON when called with `--json`.
  - Returns a non-zero exit code when the overall health is unhealthy (suitable for CI or container health probes).

```bash
# Human-readable check
python3 -m vpn_sentinel.common.health_scripts.healthcheck

# JSON output for automation
python3 -m vpn_sentinel.common.health_scripts.healthcheck --json
```

JSON schema (summary)
- `status`: `healthy` or `unhealthy`.
- `timestamp`: ISO8601 UTC timestamp.
- `checks`: object with `client_process`, `network_connectivity`, `server_connectivity` and `health_monitor`.
- `warnings`: array of short codes (for example `"server_unreachable"`, `"monitor_not_responding"`) plus any system resource warnings.

Example (curl):

```bash
# Full health
curl -sS http://localhost:8082/client/health | jq .

# Readiness
curl -sS -w "\nHTTP_STATUS:%{http_code}\n" http://localhost:8082/client/health/ready
```

Security and stability notes
- The monitor performs outbound network probes to check connectivity. In restricted environments these probes may fail and cause `network_unreachable` issues in the health report; this is expected.
- Avoid exposing the health endpoint publicly without network-level protections. If you require authentication for the health endpoints, wrap the monitor behind a reverse proxy with ACLs.
- The health monitor is optional; the client keeps no state and continues to send keepalives even if the monitor is disabled.

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

### Stop helper and PIDFILE

The health monitor wrapper supports a safe `--stop` option which reads the pidfile (see `VPN_SENTINEL_HEALTH_PIDFILE`) and attempts to stop the referenced process only if it is owned by the invoking user and looks like the health monitor:

```bash
VPN_SENTINEL_HEALTH_PIDFILE=/tmp/vpn-sentinel-health-monitor.pid python3 -m vpn_sentinel.common.health_scripts.health_monitor_wrapper --stop
```

By default the wrapper uses `/tmp/vpn-sentinel-health-monitor.pid`; override the path with `VPN_SENTINEL_HEALTH_PIDFILE` (useful in tests and smoke scripts).

## Testing & debugging
- Set `VPN_SENTINEL_DEBUG=true` for verbose logging.
- To run the health monitor on its own from a checkout:

```bash
VPN_SENTINEL_HEALTH_PORT=8082 python3 -m vpn_sentinel.common.health_scripts.health_monitor_wrapper
curl http://localhost:8082/client/health
```

## Logging
- Logs are written to stdout and follow the format:

```
[TIMESTAMP] LEVEL [COMPONENT] MESSAGE
```

Components used: `config`, `client`, `vpn-info`, `dns-test`, `api`.

## Troubleshooting
- If keepalives are not reaching the server:
  - Verify `VPN_SENTINEL_URL` and `VPN_SENTINEL_API_KEY` (or `VPN_SENTINEL_API_KEY_FILE`)
  - Ensure the container shares the VPN network namespace and has external connectivity
  - Check `VPN_SENTINEL_TLS_CERT_PATH` if the server uses a custom CA
- If DNS leak detection seems incorrect:
  - Check connectivity to `ipinfo.io`, `ip-api.com` and `1.1.1.1` from inside the container
  - Use `VPN_SENTINEL_DEBUG=true` to inspect the details
- If the health report says `client_process_not_running`: the `vpn_sentinel.client` process is not running; start the client container.

## Contributing
- Keep this README in sync with changes to `__main__.py` and the common modules it uses.
- If you add environment variables or change defaults, update this file accordingly.

## License
- MIT
