# Design: `/local-env` — Local Docker E2E Environment

- **Date:** 2026-06-21
- **Status:** Approved (design); pending implementation plan
- **Author:** Claude (with agigante80)
- **Scope:** Spec 1 of 3. This spec covers ONLY the `/local-env` skill + a trustworthy
  full E2E run on the *current* code and structure. Folder/script restructure (Spec 2)
  and code refactor (Spec 3) are deferred and will each be guarded by `/local-env verify`.

## Problem

VPNSentinel currently has **four overlapping Docker definitions** and no single, reliable
way to stand the whole system up locally and prove it works end-to-end:

- `compose.yaml` — full stack (with VPN)
- `compose-no-vpn.yaml` — no-VPN variant
- `tests/docker-compose.test.yaml` — integration test stack (isolated ports), used by CI
- `scripts/smoke/run_local_smoke.sh` — raw `docker run` E2E with its own bash assertions
  (build → run → assert keepalive → check client health → check dashboard → teardown,
  run twice for HTTP and TLS)

Assertions are duplicated between the smoke script (bash) and `tests/integration/` (pytest).
There is no one command for start/stop/rebuild/verify. Before we restructure or refactor
anything, we need a dependable regression safety net: stand the system up on local Docker
and run a full E2E.

## Goals

- One command surface — `/local-env` — for **start / stop / rebuild / status / logs / verify**.
- `verify` is a **trustworthy full E2E** on the current code: build images, bring the stack
  up gated by healthchecks, and assert the system works end-to-end.
- "Green locally" must equal "green in CI" — both drive the *same* compose stack.
- Single source of truth for E2E assertions (no bash/pytest duplication).
- The tooling is a real, human-usable CLI (not just AI prose) and is CI-reusable.

## Non-Goals (deferred to later specs)

- Folder/script restructure and renaming (Spec 2).
- Code refactor of `vpn_sentinel_common/`, client, or server (Spec 3).
- Consolidating `compose.yaml` / `compose-no-vpn.yaml` into the canonical stack (Spec 2).
- Real-VPN E2E (needs provider secrets, flaky, not CI-able). May become an opt-in
  compose profile in a later spec.
- Simulated bypass/DNS-leak fault injection (🔴/🟡 logic). Foundation first; can be added later.

## Decisions (locked during brainstorming)

1. **Sequencing:** E2E-first. Restructure and refactor are separate, later specs.
2. **Engine:** Docker Compose, a single canonical local stack with healthchecks +
   `depends_on: condition: service_healthy` for readiness (no `sleep` loops).
3. **E2E depth:** No-VPN happy path. Telegram disabled/dry-run (no real token).
4. **Verify implementation:** Reuse `pytest tests/integration/` against the live stack —
   assertions live once.
5. **Skill shape:** Thin skill (`disable-model-invocation: true`) calling a real
   `bin/local-env` CLI. Plus a thin `/local-env` command alias for ergonomics.
6. **Real E2E test (added after a mid-design finding):** Spec 1 adds a NEW dedicated,
   port-aware E2E test rather than relying on the existing suite (see Findings).

## Findings (discovered during planning — they change verify's scope)

The original plan to make `verify` simply run `pytest tests/integration/` rests on a false
premise: **the existing suite does not truly E2E-test the Docker stack.**

- `tests/integration/test_e2e.py:69` and `:135` — the only tests exercising the real
  client→server keepalive→`/status` workflow are `@unittest.skip("Temporarily skipped…")`.
  They never run.
- Even un-skipped, `test_e2e.py:63-64` target `http://localhost:5000` / `:8081`, but the
  compose stack publishes the server on host ports **15554 / 15553**
  (`tests/docker-compose.test.yaml:9-11`). They would hit nothing and `skipTest` on
  `ConnectionError` (`:132`).
- What genuinely hits the live stack today is essentially `test_dashboard.py` (correctly
  reads host port `18080` via `VPN_SENTINEL_SERVER_DASHBOARD_PORT`). The client-subprocess
  tests check the client's *own* health endpoints, not a real round-trip to the server.
- CI bridges readiness with `sleep 10` (`.github/workflows/ci-cd.yml`), not a healthcheck.

**Consequence:** wrapping the current suite would go green without proving the core flow.
Spec 1 therefore adds a genuine E2E test (below) as `verify`'s backbone. Cleaning up /
un-skipping the legacy `test_e2e.py` is deferred to Spec 2.

## Architecture

Three artifacts:

```
bin/local-env                       # real CLI (bash) — all lifecycle/verify logic
.claude/skills/local-env/SKILL.md   # thin, terse, disable-model-invocation:true → calls bin/local-env
.claude/commands/local-env.md       # 2-line alias so `/local-env <cmd>` → bin/local-env <cmd>
tests/docker-compose.test.yaml      # evolved into THE canonical local stack (no new compose file)
```

### Canonical stack: `tests/docker-compose.test.yaml`

We reuse and evolve this file rather than add a fifth compose file, because it already has
isolated host ports and is what CI's integration job uses. `bin/local-env` and CI drive the
same stack.

Required changes:
- **Restore the server healthcheck** (currently commented out) so the client's
  `depends_on: condition: service_healthy` actually gates readiness. This is the core
  readiness mechanism; without it, readiness is implicit and fragile.
- Confirm isolated host ports (current: 15554→5000, 15553→5001, 18080→8080) and document them.
- Ensure Telegram is disabled (no bot token in `tests/.env.test`) so the notification path
  runs in dry-run and is asserted not to send.
- Keep a short keepalive interval (via `tests/.env.test`) so `verify` runs quickly.

### CLI: `bin/local-env <command>`

| Command | Behavior |
|---|---|
| `start` | `docker compose ... up -d --build`; block until healthchecks pass; print API/dashboard/health URLs |
| `stop` | `docker compose ... down -v` (clean teardown, no orphan volumes/state) |
| `rebuild` | `docker compose ... build --no-cache` then `start` |
| `status` | `docker compose ... ps` + per-service health summary |
| `logs [svc]` | `docker compose ... logs -f [svc]` |
| `verify` | ensure stack healthy → `pytest tests/integration/` against live stack → summarize pass/fail → teardown (with `--keep` flag to leave it running) |
| `help` | usage |

Implementation notes:
- Pins `COMPOSE_FILE=tests/docker-compose.test.yaml` and `--env-file tests/.env.test`.
- Resolves repo root from the script location (no `/home/$USER` absolute paths).
- Idempotent pre-flight: `start`/`verify` check current state (`compose ps`) before acting.
- Propagates exit codes so CI and pre-commit can call it.
- `set -euo pipefail`; passes `shellcheck` (already in pre-commit) and `shfmt -i 2 -ci`.

### New genuine E2E test: `tests/integration/test_local_e2e.py`

A dedicated test that hard-asserts the real flow against the **running compose stack**, on
its actual host ports (read from env, with defaults matching the compose mapping). No silent
`skipTest` on connection error — if the stack is expected and unreachable, the test FAILS.

Reads (env → default):
- `VPN_SENTINEL_SERVER_HOST` → `localhost`
- `VPN_SENTINEL_E2E_API_PORT` → `15554` (host → container 5000)
- `VPN_SENTINEL_E2E_HEALTH_PORT` → `15553` (host → container 5001)
- `VPN_SENTINEL_E2E_DASHBOARD_PORT` → `18080` (host → container 8080)
- `VPN_SENTINEL_API_PATH` → `/test/v1`
- `VPN_SENTINEL_API_KEY` → `test-api-key-abcdef123456789`

Hard assertions:
- `GET health` → 200
- `POST <api_path>/keepalive` (with auth + valid payload) → 200, `status == ok`
- `GET <api_path>/status` → the posted client present, `status == alive`
- `GET /dashboard` → 200
- the compose `vpn-sentinel-client-test` container's keepalive shows up in `/status`
  (proves the real client→server round trip, not just a synthetic POST)

Gated so it only runs when the stack is up: an env flag `VPN_SENTINEL_E2E=1` (set by
`verify`); otherwise the test is skipped with a clear reason. The exact health endpoint
path/port is confirmed in the characterization task before the assertions are finalized.

### `verify` flow (the E2E)

1. Ensure host test deps are installed (`pip install -e . && pip install -r tests/requirements.txt`).
2. Build + `up -d`; Compose healthchecks gate readiness (no `sleep` guessing).
3. Export the E2E env vars and run, against the live stack:
   - `tests/integration/test_local_e2e.py` (the genuine backbone), and
   - `tests/integration/test_dashboard.py` (already stack-aware).
4. Summarize pass/fail; tear down (unless `--keep`).

The new E2E test is the trustworthy assertion. Broader reuse/cleanup of the rest of
`tests/integration/` (un-skipping `test_e2e.py`, fixing ports) is deferred to Spec 2.

### Skill: `.claude/skills/local-env/SKILL.md`

- Frontmatter: `name: local-env`, `disable-model-invocation: true` (only runs on explicit
  invocation — correct for something that starts/stops containers), a `description` for
  discovery.
- Body: terse — one line of purpose, the command table, and "run `bin/local-env <command>`".
  Pre-flight reminder to check `bin/local-env status` before acting. Every line is recurring
  token cost, so no narration.

### Command alias: `.claude/commands/local-env.md`

Thin wrapper: `argument-hint: "[start|stop|rebuild|status|logs|verify]"`, body runs
`bin/local-env $ARGUMENTS` and reports the result.

## Retirements

- **Delete `scripts/smoke/run_local_smoke.sh`** (and its `scripts/smoke/` helpers/certs/logs
  artifacts if unused elsewhere). Its build/keepalive/health/dashboard assertions are fully
  covered by `verify` → `tests/integration/`. The TLS iteration it provided is the only
  unique coverage; TLS E2E is noted as a candidate for a later opt-in profile (out of scope here).

## Settings

Add to `.claude/settings.json` allow:
- `Bash(bin/local-env:*)` and `Bash(./bin/local-env:*)` — the CLI is the controlled entry
  point (its internal commands are fixed), so a wildcard here is acceptable and lets the
  skill run without prompts.

## Testing strategy

- `bin/local-env help` and `status` work without Docker side effects (status degrades
  gracefully when nothing is running).
- `shellcheck` + `shfmt` clean.
- The definitive proof is `bin/local-env verify` going green locally and in CI.

## Error handling

- Missing Docker / compose → clear message, non-zero exit.
- Healthcheck never passes within timeout → dump `compose ps` + recent logs, non-zero exit.
- `pytest` failures → surfaced verbatim, non-zero exit, stack left up only with `--keep`.
- Ctrl-C during `start`/`verify` → trap to tear down (no orphaned containers).

## Rollout / acceptance

- `tests/integration/test_local_e2e.py` hard-asserts the real client→server→status→dashboard
  flow against the live stack and FAILS (not skips) if the stack is unreachable when expected.
- `bin/local-env verify` passes locally from a clean checkout and is the command that runs the
  genuine E2E.
- Readiness is gated by a restored server healthcheck (no `sleep`).
- CI integration job can call `bin/local-env verify` (or continues to drive the same stack).
- `/local-env` (skill or command) runs each subcommand.
- Smoke script removed; no dangling references in docs/CI.
- A GitHub issue tracks this request and links this spec.

## Follow-on specs (context, not scope)

- **Spec 2 — Restructure:** consolidate compose files, reorganize `scripts/`, `bin/`, `tests/`,
  and the folder layout to a clean convention. Every move verified by `bin/local-env verify`.
- **Spec 3 — Code refactor:** improve `vpn_sentinel_common/` module boundaries and the
  client/server entry points. Guarded by Specs 1–2.
