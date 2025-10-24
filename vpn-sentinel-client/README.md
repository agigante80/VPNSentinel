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
- Uses external services to determine VPN exit IP and location (primary: `ipinfo.io`, fallback: `ip-api.com`)
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
  - Description: Forces which geolocation service to use: `auto`, `ipinfo.io`, or `ip-api.com`
  - Default: `auto` (tries `ipinfo.io` then falls back to `ip-api.com`)

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
When `VPN_SENTINEL_HEALTH_MONITOR` is enabled and `health-monitor.sh` exists, the client starts it in the background. The health monitor provides a lightweight readiness/health endpoint for container orchestrators (the default port is `8082`).

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
