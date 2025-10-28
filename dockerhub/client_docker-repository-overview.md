# VPN Sentinel Client Docker image

Summary
-------
The VPN Sentinel Client is a compact, Alpine-based container that monitors VPN connectivity, performs DNS-leak detection, and periodically reports keepalive and diagnostic data to the VPN Sentinel Server. It is intended to run inside a VPN network namespace (for example `network_mode: service:gluetun`) so that connectivity and DNS behavior are validated through the VPN tunnel.

Key features
------------
- Lightweight Alpine image with a contained Python virtualenv for an optional Flask health monitor
- Periodic keepalive reports to a configurable server API (`VPN_SENTINEL_URL` / `VPN_SENTINEL_API_PATH`)
- DNS leak detection and geolocation lookups (ipinfo.io fallback)
- Built-in container HEALTHCHECK script and optional embedded health endpoint for orchestration
- Designed for Docker Compose and CI-friendly usage with minimal runtime dependencies

Quickstart
----------
Pull and run the image (example):

```bash
docker pull agigante80/vpn-sentinel-client:latest
docker run --rm \
  -e VPN_SENTINEL_URL="http://your-server:5000" \
  -e VPN_SENTINEL_API_PATH="/api/v1" \
  -e VPN_SENTINEL_CLIENT_ID="office-vpn" \
  agigante80/vpn-sentinel-client:latest
```

Dockerfile snippet
------------------
This image is built from `alpine:latest`, installs `curl`, `python3`, and creates a Python virtualenv at `/opt/venv`. Application scripts are installed to `/app/` and the default `CMD` is `/app/vpn-sentinel-client.sh`.

Common environment variables
----------------------------
- `VPN_SENTINEL_URL` — Base URL of the monitoring server (required)
- `VPN_SENTINEL_API_PATH` — API path prefix (default: `/api/v1`)
- `VPN_SENTINEL_CLIENT_ID` — Unique client identifier
- `VPN_SENTINEL_API_KEY` — Optional API key for server authentication
- `VPN_SENTINEL_HEALTH_MONITOR` — Enable or disable embedded health monitor
- `VPN_SENTINEL_HEALTH_PORT` — Port for embedded health server when enabled

Tags and variants
-----------------
- `latest` — the most recent stable build (default tag)
- Branch/sha tags — CI will create branch/sha tags for traceability

Documentation & support
-----------------------
Full source, examples, and deployment instructions are in the GitHub repository:

https://github.com/agigante80/VPNSentinel

License
-------
This project is licensed under the MIT License. See the `LICENSE` file in the repository for details.

Maintainer
----------
VPN Sentinel Project — GitHub: `agigante80` — https://github.com/agigante80/VPNSentinel
