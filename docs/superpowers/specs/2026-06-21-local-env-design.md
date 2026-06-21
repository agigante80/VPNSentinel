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

### `verify` flow (the E2E)

1. Build + `up -d`; Compose healthchecks gate readiness (no `sleep` guessing).
2. Run `pytest tests/integration/` against the live stack. These tests already assert:
   - client keepalive reaches server (≥2 cycles),
   - `GET /status` reports the client,
   - client `/health`, `/health/ready`, `/health/startup`,
   - dashboard returns 200.
3. Summarize pass/fail; tear down (unless `--keep`).

Assertions live once, in `tests/integration/`. Same suite runs in CI.

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

- `bin/local-env verify` passes locally from a clean checkout.
- CI integration job can call `bin/local-env verify` (or continues to drive the same stack).
- `/local-env` (skill or command) runs each subcommand.
- Smoke script removed; no dangling references in docs/CI.
- A GitHub issue tracks this request and links this spec.

## Follow-on specs (context, not scope)

- **Spec 2 — Restructure:** consolidate compose files, reorganize `scripts/`, `bin/`, `tests/`,
  and the folder layout to a clean convention. Every move verified by `bin/local-env verify`.
- **Spec 3 — Code refactor:** improve `vpn_sentinel_common/` module boundaries and the
  client/server entry points. Guarded by Specs 1–2.
