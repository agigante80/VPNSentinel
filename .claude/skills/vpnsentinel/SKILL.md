---
name: vpnsentinel
description: Expert on the VPNSentinel codebase, VPN monitoring operations, DNS leak detection, and the distributed client-server architecture. Activate for any question about VPNSentinel development, debugging, deployment, or monitoring.
---

# VPN Sentinel Expert

You are a specialist in the VPNSentinel project — a distributed real-time VPN monitoring system. You
have deep knowledge of the full codebase, operational patterns, and failure modes.

## System Architecture

**Distributed client-server model:**

```
[VPN Client container]          [VPN Server container]
  vpn-sentinel-client.py          vpn-sentinel-server.py
  - Keepalive loop (60s)   POST → API :5000  /keepalive
  - Public IP detection           - Status tracking (in-memory)
  - DNS leak detection            - Telegram notifications
  - Health monitor subprocess     - Web dashboard :8080
  network_mode: service:vpn       - Health endpoint :8081
```

**Key constraint:** The client container must run inside the VPN network namespace
(`network_mode: service:vpn-client`). Without this, it cannot detect VPN bypass (client IP would
always equal server IP).

## Traffic Light Status Model

| Status | Condition | Alert Level |
|---|---|---|
| 🟢 Green | VPN routing correctly, DNS clean | None |
| 🟡 Yellow | DNS leaking (DNS resolves outside VPN) | Warning |
| 🔴 Red | VPN bypass — client public IP matches server IP | Critical |

**Red alert logic** (`api_routes.py`): Compare `client_public_ip` with `server_public_ip`. If equal,
the client is not routing through the VPN.

**Yellow alert logic** (`network.py`): Parse Cloudflare DNS trace response. If `loc=` code doesn't
match expected VPN server location, DNS is leaking.

## DNS Leak Detection

1. Primary: `dig TXT whoami.cloudflare @1.1.1.1 +short` — returns DNS resolver location
2. Fallback: HTTP GET `https://1.1.1.1/cdn-cgi/trace` or `https://www.cloudflare.com/cdn-cgi/trace`
3. Parse response: `loc=XX` (2-letter country), `colo=YYY` (Cloudflare datacenter)
4. Compare against expected VPN server country (`country_codes.py`)

If Cloudflare is unreachable, DNS leak detection silently fails — this is a known limitation.

## IP Geolocation Cascade

Three providers tried in sequence (all return: `public_ip`, `country`, `city`, `org`):

1. `https://ipinfo.io/json` — primary; richest data
2. `https://ip-api.com/json` — fallback #1
3. `https://ipwhois.app/json` — fallback #2

If all three fail (e.g., air-gapped network), geolocation fields are empty. The monitoring still
works for bypass detection (just missing location context).

## Flask Multi-App Architecture

Three Flask applications run as separate threads in `vpn-sentinel-server.py`:

| Port | App | Purpose |
|---|---|---|
| 5000 | API app | `POST /keepalive`, `GET /status` — client communication |
| 8080 | Dashboard | Web UI — traffic light table, log viewer, auto-refresh |
| 8081 | Health | `/health`, `/health/ready`, `/health/startup` — Docker healthcheck |

**Thread safety:** `client_status = {}` in `api_routes.py` is shared state accessed by all three
threads. Writes happen in the `POST /keepalive` handler; reads in dashboard and status endpoints.

## ⚠️ Critical: In-Memory State

```python
# api_routes.py
client_status = {}  # ALL client data lives here
```

**Server restart = all client history lost.** There is no persistence layer. Clients re-register on
their next keepalive cycle (up to 60 seconds gap). This is by design but always worth flagging in PRs
that touch restart logic or add new features that depend on historical data.

## Client Keepalive Loop

Every 60 seconds (configurable via `VPN_SENTINEL_INTERVAL`), the client:
1. Gets its public IP via geolocation cascade
2. Gets DNS location via Cloudflare trace
3. POSTs JSON payload to `http://<server>:5000/keepalive`
4. Server computes traffic light status, updates `client_status`, sends Telegram if status changed

**Timeout detection:** Server marks clients as offline after `VPN_SENTINEL_TIMEOUT` seconds (default
1800 = 30 min) without a keepalive. A background cleanup thread runs every 60s to evict stale clients.

## Key Files

| File | Purpose |
|---|---|
| `vpn-sentinel-client/vpn-sentinel-client.py` | Client entry point (keepalive loop, subprocess management) |
| `vpn-sentinel-server/vpn-sentinel-server.py` | Server entry point (starts 3 Flask apps + cleanup thread) |
| `vpn_sentinel.common/api_routes.py` | Core API: keepalive handler, client status tracking |
| `vpn_sentinel.common/dashboard_routes.py` | Web UI (largest module) |
| `vpn_sentinel.common/telegram.py` | Telegram Bot API: long polling, message formatting |
| `vpn_sentinel.common/network.py` | DNS trace parsing |
| `vpn_sentinel.common/geolocation.py` | IP geolocation with cascade fallback |
| `vpn_sentinel.common/security.py` | Rate limiting (30 req/min/IP), IP whitelist |
| `vpn_sentinel.common/health.py` | Health check schema and component status |
| `vpn_sentinel.common/config.py` | All config from env vars (`VPN_SENTINEL_*` prefix) |

## Development Workflow

**Run unit tests:**
```bash
python -m pytest tests/unit/ -v --tb=short
```

**Run with coverage:**
```bash
python -m pytest tests/unit/ --cov=vpn_sentinel.common --cov-report=term-missing
```

**Full suite (installs deps, unit + integration, coverage, cleanup):**
```bash
./tests/run_tests.sh --all
```

**Check linting:**
```bash
flake8 --max-line-length=120 vpn_sentinel.common/ vpn-sentinel-client/ vpn-sentinel-server/
```

**Check server status (from inside container or local):**
```bash
curl -s http://localhost:5000/status | python3 -m json.tool
```

**Test suite structure:**
- `tests/unit/` — pure logic tests, fast, no Docker needed
- `tests/integration/` — full Docker stack, slower
- `tests/smoke/` — real-world shell scripts for manual validation
- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.network`, `@pytest.mark.docker`
- Coverage requirement: 80% minimum (enforced in `pyproject.toml`)

## Deployment Scenarios

Four deployment modes are documented in `deployments/`:

| Mode | Description |
|---|---|
| `all-in-one` | Client and server on same host; client uses host VPN |
| `client-standalone` | Client only; reports to remote server |
| `client-with-vpn` | Client + VPN service in Docker (network isolation via `network_mode`) |
| `server-central` | Central server monitoring multiple remote clients |

## Telegram Integration

- Bot uses long polling (`getUpdates` with offset tracking)
- Commands: `/start`, `/status`, `/help` — parsed from message text
- Notifications sent via `sendMessage` with HTML formatting
- Rate limit risk: Telegram throttles bots that send too many messages; batching logic in
  `telegram.py` handles bursts
- All alerts include: client ID, public IP, location, DNS status, ISP/provider

## Common Failure Modes to Watch For

1. **Client IP = server IP** → VPN bypass (Red alert) — check VPN service inside client container
2. **DNS resolves outside VPN country** → DNS leak (Yellow) — check DNS settings in VPN config
3. **No keepalives received for 30+ min** → client timeout — check client container logs and network
4. **Geolocation shows wrong country** → ISP/VPN provider using anycast; may be false Yellow
5. **Cloudflare unreachable** → DNS detection silently disabled; Green even if DNS is leaking
6. **Server restart** → all client data cleared; wait one keepalive cycle (60s) to repopulate
7. **Rate limit (30 req/min)** → legitimate clients with very short keepalive intervals may get blocked

## Code Review Checklist

When reviewing PRs, always check:
- [ ] Any new state stored in `client_status` or similar dicts → will be lost on restart; document it
- [ ] New external HTTP calls → add retry/fallback logic; don't let a single provider failure break the flow
- [ ] Flask route handlers that access shared `client_status` → thread safety
- [ ] New Telegram notifications → can they burst? Add rate limiting if yes
- [ ] Tests at 80%+ coverage for new code
- [ ] flake8 compliance (max line length 120)
