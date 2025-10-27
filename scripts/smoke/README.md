# Smoke tests (local)

This directory contains a small local smoke-test orchestrator used during development to validate the server + client interaction end-to-end on your machine using Docker.

Quick overview
- Script: `scripts/smoke/run_local_smoke.sh`
- Purpose: build server and client images, start both containers briefly, assert the server receives a keepalive from the client, probe client health endpoints, and verify the dashboard is reachable.
- Runs twice: first without TLS, then with TLS (the script will auto-generate self-signed certs if none are present).

How to run

From the repository root run:

```bash
bash scripts/smoke/run_local_smoke.sh
```

What the script does
- Cleans previous debug containers and removes local `vpn-sentinel-*:local` images (if present).
- Builds `vpn-sentinel-server:local` and `vpn-sentinel-client:local` images.
- Starts the server container and waits for the server API and health endpoints.
- Starts the client container (health monitor enabled) and waits for the first keepalive to arrive at the server.
- Probes the client health endpoints via host port 8082:
  - `http://localhost:8082/client/health`
  - `http://localhost:8082/client/health/ready`
  - `http://localhost:8082/client/health/startup`
- Probes the dashboard at `http(s)://<server-ip>:8080/dashboard`.
- Repeats the run with TLS enabled. If `scripts/smoke/certs` doesn't contain `cert.pem`/`key.pem`, the script will generate temporary self-signed certs and mount them into the server container. When using self-signed certs, curl is invoked with `-k` and the client is started with `VPN_SENTINEL_ALLOW_INSECURE=true` so it accepts the test certs.

Log files and locations
- Per-run logs are written under: `scripts/smoke/logs/`.
- Each run creates a timestamped directory with a `_no` (no TLS) or `_yes` (TLS) suffix, for example:
  - `scripts/smoke/logs/20251027T101818Z_no`
  - `scripts/smoke/logs/20251027T101824Z_yes`
- Each directory contains:
  - `server.log` — stdout/stderr captured from the server container.
  - `client.log` — stdout/stderr captured from the client container.
  - `status.txt` — short status summary produced by the smoke script.
  - `dashboard.html` — the HTML returned when probing the dashboard (if reachable).

Interpreting results
- Successful run messages (script stdout) include:
  - `Server received keepalive from 'smoke-client'` — confirms server saw client's keepalive.
  - `Client health endpoints OK` — confirms all `/client/health*` endpoints responded.
  - `Dashboard reachable` — confirms dashboard is serving.
  - `Both smoke iterations passed` — final success message.
- If an iteration fails, check the logs directory for the failing run and inspect `server.log` and `client.log` for errors. Common causes:
  - Port conflict on host 8082 (used to map client health port). Use `ss -ltnp | grep ':8082'` to find conflicts and stop interfering containers.
  - The embedded client health monitor didn't start or crashed. Look for `Health monitor started (PID: ...)` in `client.log` and any Python/Flask tracebacks.
  - TLS certificate issues during the TLS iteration: the script generates temporary certs by default. If you prefer to use stable certs, place `cert.pem` and `key.pem` in `scripts/smoke/certs/` before running.

Troubleshooting tips
- If the client health endpoint is returning `Connection refused` or `Connection reset by peer`:
  1. Check that nothing else is binding port 8082 on the host.
  2. Start the containers manually (if you need to debug) and inspect client logs:
     - `docker ps -a` to find the client container id
     - `docker logs <client-container-id>`
  3. Exec into the client container and try an internal curl to `127.0.0.1:8082` to confirm whether the Flask health server bound the port.

Maintenance notes
- The smoke script is intended for local developer quick-checks and not as a production test harness. It uses self-signed certs for TLS iteration and exposes ports on the host for convenience.
- Consider adding persistent certs or integrating the smoke run into CI if you want repeatable CI-level checks (update the script to accept pre-generated certs via env vars).

If you'd like, I can:
- Commit this README into the repo (already done), or
- Extend the README with a small troubleshooting checklist with exact grep commands to speed debugging.

Happy to expand or adapt the README for your preferred workflow.
