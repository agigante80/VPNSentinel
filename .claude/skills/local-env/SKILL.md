---
name: local-env
description: Manage the VPNSentinel local Docker E2E environment — start, stop, rebuild, status, logs, and a genuine end-to-end verify. Use when asked to bring the stack up locally, tear it down, or prove the system works end-to-end on Docker before/after changes.
disable-model-invocation: true
---

# local-env

Run the project's local Docker E2E stack via the CLI. Always prefer the CLI over ad-hoc
`docker compose` so local == CI.

Pre-flight: run `bin/local-env status` before acting.

| Command | Use |
|---|---|
| `bin/local-env start` | Build + start; waits until the server is healthy; prints URLs |
| `bin/local-env stop` | Tear down (`down -v`) |
| `bin/local-env rebuild` | `--no-cache` rebuild, then start |
| `bin/local-env status` | Container + health status |
| `bin/local-env logs [svc]` | Follow logs |
| `bin/local-env verify` | Full E2E: up (healthy) → live-stack pytest → teardown. `--keep` leaves it up. |

`verify` is the regression safety net — run it before and after any restructure/refactor.
Stack: `tests/docker-compose.test.yaml` (API :15554, health :15553, dashboard :18080).
