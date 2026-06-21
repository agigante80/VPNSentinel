---
description: Manage the local Docker E2E environment (start/stop/rebuild/status/logs/verify)
argument-hint: "[start|stop|rebuild|status|logs|verify] (default: status)"
---

Run `bin/local-env $ARGUMENTS` (default to `status` if no argument is given) and report the
result. For `verify`, surface the pytest summary and the final PASS/FAIL line; do not claim
success unless the command exits 0.
