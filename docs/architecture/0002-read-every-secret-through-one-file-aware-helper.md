# 0002. Read every secret through one helper supporting the Docker `_FILE` convention

- Status: accepted
- Date: 2026-11-11

## Context

- Secrets (`VPN_SENTINEL_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`) are read directly from
  environment variables in several modules (api_routes.py, payload.py, telegram.py).
- Environment variables show in `docker inspect`, and Compose or Swarm secrets users, who receive
  secrets as files, cannot use them.
- A `NAME_FILE` variable is silently ignored today, so a server configured that way starts with auth
  disabled.
- `VPN_SENTINEL_METRICS_TOKEN` (ADR 0001) is a new secret that needs the same handling.
- Tracked in issue #139.

## Options considered

- **A. Env vars only (status quo).** Pro: no work. Con: secrets show in `docker inspect`;
  Compose/Swarm secrets users cannot use files; a `_FILE` var is silently ignored and the server
  starts with auth disabled.
- **B. Generic `_FILE` support via one helper (chosen).** Pro: matches official images (postgres,
  mysql), small change, fail closed. Con: more config paths to test.
- **C. Document env_file only.** Pro: no code. Con: does not keep secrets out of the container
  environment.

## Decision

Option B. Every secret (`VPN_SENTINEL_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`,
`VPN_SENTINEL_METRICS_TOKEN`) is read through one helper, `read_secret(name)` in
`common/config.py`, implementing the Docker `_FILE` convention:

- `NAME_FILE` points to a file whose content, with all trailing `\r` and `\n` stripped, is the value.
- An empty file (empty after the strip) is fatal, because an empty API key would disable auth.
- Setting both `NAME` and `NAME_FILE` is a fatal error.
- An unreadable file is fatal: fail closed, never fall back to auth disabled.
- Secret values are never logged.

## Consequences

- Secrets can be kept out of the container environment via Compose or Swarm secrets.
- Misconfiguration stops startup instead of silently disabling auth.
- More configuration paths (env, file, both, unreadable file) must be tested.
- All direct `os.getenv` reads of these secrets must move to the helper.

## Sources

- src/vpn_sentinel/common/api_routes.py:21
- src/vpn_sentinel/common/payload.py:89
- src/vpn_sentinel/common/telegram.py:14
- https://docs.docker.com/compose/how-tos/use-secrets/ (checked 2026-11-11)
- https://github.com/docker-library/postgres/blob/master/docker-entrypoint.sh (checked 2026-11-11)
- Issue #139

## Revisit when

- A secrets manager integration (Vault or similar) is requested.
