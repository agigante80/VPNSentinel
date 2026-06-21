# Local Docker E2E Stack — Endpoint Characterization

Recorded: 2026-06-21  
Stack: `tests/docker-compose.test.yaml` with `tests/.env.test`  
Host port mappings: 15554→5000 (API), 15553→5001 (health), 18080→8080 (dashboard)

---

## Health Endpoint

### Finding: only the dedicated health port works without auth

| URL | Status | Body |
|-----|--------|------|
| `http://localhost:15553/health` | **200 OK** | `{"message":"VPN Sentinel Health Server is running","server_time":"unknown","status":"ok"}` |
| `http://localhost:15554/test/v1/health` | **404 NOT FOUND** | HTML 404 page (route not registered on API app) |

**Canonical health URL (for E2E tests): `http://localhost:15553/health`**

The server runs two separate Flask apps:
- Port 5001 (host 15553): `health_app` — no auth, serves `/health`, `/health/ready`, `/health/startup`
- Port 5000 (host 15554): `api_app` — requires `X-API-Key` header, no `/health` route registered

Note: The Dockerfile's built-in HEALTHCHECK uses `wget` (not `curl`) because Alpine 3.23+ removed the `curl` package from the base image. The compose healthcheck was updated to use `wget -qO-` accordingly.

Compose healthcheck that actually works:
```yaml
healthcheck:
  test: ["CMD-SHELL", "wget -qO- http://127.0.0.1:5001/health || wget -qO- http://127.0.0.1:5000/test/v1/health || exit 1"]
  interval: 5s
  timeout: 5s
  retries: 12
  start_period: 20s
```

---

## Authentication

API endpoints require `X-API-Key` header (NOT `Authorization: Bearer`).

```
X-API-Key: test-api-key-abcdef123456789
```

Without this header, the API returns:
```
HTTP/1.1 401 UNAUTHORIZED
{"error":"Authentication required","message":"X-API-Key header is required"}
```

---

## POST /test/v1/keepalive

```bash
curl -i -X POST http://localhost:15554/test/v1/keepalive \
  -H "X-API-Key: test-api-key-abcdef123456789" \
  -H "Content-Type: application/json" \
  -d '{"client_id":"char-probe","timestamp":"2026-06-21T00:00:00+00:00","public_ip":"203.0.113.9","status":"alive","location":{"country":"US","city":"X","region":"Y","org":"AS1 Z","timezone":"UTC"},"dns_test":{"location":"US","colo":"NYC"}}'
```

**Response: 200 OK**
```json
{"message":"Keepalive received","server_time":"2026-06-21T09:51:08.860477+00:00","status":"ok"}
```

Shape: `{"message": string, "server_time": ISO-8601 string, "status": "ok"}`

---

## GET /test/v1/status

```bash
curl -s http://localhost:15554/test/v1/status \
  -H "X-API-Key: test-api-key-abcdef123456789" | python3 -m json.tool
```

**Response: 200 OK** — top-level object keyed by `client_id`:

```json
{
    "char-probe": {
        "city": "X",
        "client_version": "Unknown",
        "country": "US",
        "dns_colo": "NYC",
        "dns_loc": "US",
        "ip": "203.0.113.9",
        "last_seen": "2026-06-21T09:51:08.860227+00:00",
        "location": "X, Y, US",
        "provider": "AS1 Z",
        "region": "Y",
        "timezone": "UTC"
    },
    "test-client-docker": {
        "city": "Madrid",
        "client_version": "1.0.0-dev",
        "country": "ES",
        "dns_colo": "MAD",
        "dns_loc": "ES",
        "ip": "79.112.62.172",
        "last_seen": "2026-06-21T09:50:27.935135+00:00",
        "location": "Madrid, Madrid, ES",
        "provider": "AS57269 DIGI SPAIN TELECOM S.A",
        "region": "Madrid",
        "timezone": "Europe/Madrid"
    }
}
```

Key findings:
- Top-level keys are `client_id` strings
- Each entry has: `city`, `client_version`, `country`, `dns_colo`, `dns_loc`, `ip`, `last_seen`, `location`, `provider`, `region`, `timezone`
- **`test-client-docker` appears in `/status`** — the compose client container sends keepalives successfully
- `last_seen` is ISO-8601 with UTC offset

---

## GET /dashboard (port 18080)

```bash
curl -i http://localhost:18080/dashboard
```

**Response: 200 OK** — returns full HTML dashboard page (Content-Type: text/html; charset=utf-8)

No authentication required for the dashboard.

---

## Summary for Task 2 (E2E test defaults)

| Variable | Value |
|----------|-------|
| Health URL (200 OK, no auth) | `http://localhost:15553/health` |
| API base URL | `http://localhost:15554/test/v1` |
| Auth header | `X-API-Key: test-api-key-abcdef123456789` |
| Keepalive success JSON fields | `status`, `message`, `server_time` |
| Status JSON shape | Top-level dict keyed by client_id |
| Client ID in status | `test-client-docker` (present after first keepalive) |
| Dashboard URL | `http://localhost:18080/dashboard` → 200 HTML |
| Dashboard auth | None required |
