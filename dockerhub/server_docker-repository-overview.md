# VPN Sentinel Server Docker image

Summary
-------
The VPN Sentinel Server is a Flask-based monitoring server that ingests keepalive messages from VPN Sentinel Clients, aggregates client health data, detects DNS leaks, and can send alerts via Telegram. The server also exposes a web dashboard for real-time monitoring and management.

Key features
------------
- Flask REST API for keepalive ingestion and client status endpoints
- Web dashboard for visualizing client state and recent events
- DNS leak detection and aggregated client health metrics
- Optional Telegram integration for alerting and interactive commands
- Runs as a non-root user inside the container and uses pinned Python packages

Quickstart
----------
Pull and run the server image (example):

```bash
docker pull agigante80/vpn-sentinel-server:latest
docker run --rm -p 5421:5000 \
  -e TELEGRAM_BOT_TOKEN=xxx \
  -e TELEGRAM_CHAT_ID=yyy \
  agigante80/vpn-sentinel-server:latest
```

Dockerfile snippet
------------------
This image is built from `python:3.12-alpine`, installs runtime Python packages (Flask, requests, psutil), and runs `vpn-sentinel-server.py` as a non-root user.

Common environment variables
----------------------------
- `TELEGRAM_BOT_TOKEN` — Telegram bot token for alert delivery
- `TELEGRAM_CHAT_ID` — Telegram chat id to send alerts to
- `VPN_SENTINEL_API_KEY` — Optional API key expected from clients

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
MIT — see `LICENSE` in the repository.

Maintainer
----------
VPN Sentinel Project — GitHub: `agigante80` — https://github.com/agigante80/VPNSentinel

Docker Hub
----------
Client image: https://hub.docker.com/r/agigante80/vpn-sentinel-client
