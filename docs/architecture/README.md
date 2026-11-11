# Architecture

The long-form architecture description lives in [../ARCHITECTURE.md](../ARCHITECTURE.md); the
repository layout and runtime wiring are summarised in [../../CLAUDE.md](../../CLAUDE.md).

This folder holds the architecture decision records (ADRs). A new ADR is written as `proposed`;
only the maintainer sets `accepted`, and an accepted ADR is never edited, only superseded by a
newer one.

## ADR index

| ADR | Title | Status | Decision (one line) |
|---|---|---|---|
| [0001](0001-metrics-public-by-default-with-optional-bearer-token.md) | Keep /metrics public by default, with an optional dedicated bearer token | proposed | /metrics stays public by default; optional VPN_SENTINEL_METRICS_TOKEN requires a constant-time-checked bearer token (401 otherwise) |
| [0002](0002-read-every-secret-through-one-file-aware-helper.md) | Read every secret through one helper supporting the Docker `_FILE` convention | proposed | All secrets go through read_secret(name) with `_FILE` support; both set or unreadable file is fatal; values never logged |
