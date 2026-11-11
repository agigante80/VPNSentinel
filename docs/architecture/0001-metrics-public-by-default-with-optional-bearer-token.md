# 0001. Keep /metrics public by default, with an optional dedicated bearer token

- Status: proposed
- Date: 2026-11-11

## Context

- The Prometheus `/metrics` endpoint is served by the health app (port 8081).
- Metrics carry client IDs and statuses, never IPs or geolocation.
- `/health` is already public on the same port.
- The root `compose.yaml` does not publish port 8081.
- `VPN_SENTINEL_METRICS_ENABLED=false` turns the endpoint off (404).
- A user who publishes 8081 exposes client IDs and statuses to anyone who can reach it.
- Tracked in issue #140.

## Options considered

- **A. Keep public as is.** Pro: zero setup, works with Prometheus out of the box. Con: a user who
  publishes 8081 exposes client IDs and statuses.
- **B. Opt-in (default off).** Pro: safest default. Con: hides the newly shipped feature; users must
  find the switch.
- **C. Behind the main API key.** Pro: reuses existing auth. Con: the scraper must hold the main API
  key, so a leaked Prometheus config exposes more than metrics.
- **D. Public by default plus an optional dedicated bearer token (chosen).** Pro: zero setup by
  default, a separate low-privilege secret for exposed setups, Prometheus sends bearer auth natively.
  Con: one more config path to test.

## Decision

Option D. `/metrics` on the health app (port 8081) stays enabled and unauthenticated by default.
An optional `VPN_SENTINEL_METRICS_TOKEN` is added; when it is set, `/metrics` requires
`Authorization: Bearer <token>`, compared in constant time, and answers 401 for a missing or wrong
token.

## Consequences

- Default installs keep working with a plain Prometheus scrape config and no setup.
- Operators who publish 8081 can protect metrics with a secret separate from the main API key, so a
  leaked scrape config does not grant API access.
- One more configuration path (token set, token missing, token wrong) must be tested.

## Sources

- src/vpn_sentinel/common/health_routes.py
- src/vpn_sentinel/common/metrics.py
- Merge commit 7da0366 (v1.1.12)
- https://prometheus.io/docs/prometheus/latest/configuration/configuration/#scrape_config (checked 2026-11-11)
- https://prometheus.io/docs/guides (checked 2026-11-11)
- Issue #140

## Revisit when

- Metrics gain any IP or geolocation label, or
- the shipped compose publishes port 8081.
