# VPN Sentinel Client (agigante80/vpn-sentinel-client)

Lightweight VPN monitoring client container. Designed to run inside a VPN network namespace (for example `network_mode: service:gluetun`) to monitor connectivity, detect DNS leaks, and send periodic keepalive messages to the VPN Sentinel Server.

Key features
- Minimal Alpine-based image with a Python virtualenv for the optional Flask health monitor
- Periodic keepalive posts to a configurable server API
- DNS leak detection and geolocation lookups (ipinfo.io by default)
- Included container healthcheck and an optional embedded Flask health endpoint
- Designed for Docker Compose/CI usage and small footprint deployments

How it relates to the server
- Sends keepalive messages and diagnostics to `agigante80/vpn-sentinel-server`.
- The server receives keepalives and aggregates status for all clients; see the server repo for deployment and API details.

Quick start (example)
```bash
docker pull agigante80/vpn-sentinel-client:latest
docker run --rm \
  -e VPN_SENTINEL_URL="http://your-server:5000" \
  -e VPN_SENTINEL_API_PATH="/api/v1" \
  -e VPN_SENTINEL_CLIENT_ID="office-vpn" \
  agigante80/vpn-sentinel-client:latest
```

Where to find the source
- GitHub: https://github.com/agigante80/VPNSentinel

Tips
- When running in CI or thin images, preserve `PATH` so the bundled virtualenv Python (`/opt/venv/bin`) remains discoverable by health scripts.
- Use `VPN_SENTINEL_HEALTH_MONITOR=true` to enable the embedded health endpoint (the client ships a health-monitor implementation).
