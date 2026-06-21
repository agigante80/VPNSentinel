---
description: Run the VPNSentinel test suite (unit by default; pass "all" or "integration" to widen scope)
argument-hint: "[unit|integration|all]  (default: unit)"
---

Run the VPNSentinel tests and report results.

Scope requested: `$ARGUMENTS` (default to unit tests if empty).

- **unit / empty:** `python -m pytest tests/unit/ --tb=short --cov=vpn_sentinel.common --cov-report=term`
- **integration:** `./tests/run_tests.sh --integration` (requires a running server / Docker)
- **all:** `./tests/run_tests.sh --all`

After running, summarize: pass/fail counts, any failures with their assertion output, and the
coverage percentage. The coverage gate is 80% — call out if it's below. If tests fail, do NOT claim
success; surface the failing output.
