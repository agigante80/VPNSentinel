# VPN Sentinel Server (agigante80/vpn-sentinel-server)

Python Flask-based monitoring server for VPN Sentinel clients. Receives keepalive messages, performs DNS leak detection, and can send alerts/notifications (Telegram integration supported).

Key features
- Flask REST API for keepalive ingestion and status endpoints
- DNS leak detection and client health aggregation
- Optional Telegram integration for alerts and interactive commands
- Built with pinned Python packages and runs as a non-root `appuser` inside the container

How it relates to the client
- Receives keepalive posts from `agigante80/vpn-sentinel-client` and records client states.
- The client is intended to run inside VPN containers and report via the API exposed by this server.

Quick start (example)
```bash
docker pull agigante80/vpn-sentinel-server:latest
docker run --rm -p 5421:5000 \
  -e TELEGRAM_BOT_TOKEN=xxx \
  -e TELEGRAM_CHAT_ID=yyy \
  agigante80/vpn-sentinel-server:latest
```

Where to find the source
- GitHub: https://github.com/agigante80/VPNSentinel

Notes
- The server exposes a health endpoint used by the Docker HEALTHCHECK (adjust the Dockerfile's HEALTHCHECK URL if your runtime changes ports).
- For production, run behind a reverse proxy (nginx) with TLS termination and use environment secrets for tokens/keys.
