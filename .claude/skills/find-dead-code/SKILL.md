---
name: find-dead-code
description: Find genuinely dead / unused / unreachable SOURCE code in VPNSentinel — unused functions, classes, methods, and unreachable branches that flake8's local-scope rules (F401/F811/F841) miss. Wraps vulture with a curated allowlist for this project's dynamic-reference patterns (Flask routes, console_scripts entry points, health subprocesses, the re-export shim, Telegram string dispatch, daemon threads) so findings are low-noise and safe to act on. Use when asked to "find dead code", "remove unused code", "what code is unused", "dead-code scan", or "clean up the codebase" before a refactor or release.
---

<!-- find-dead-code-version: 1 -->

# Find Dead Code (VPNSentinel)

Locate genuinely-dead source code in `src/vpn_sentinel/` so it can be removed safely — WITHOUT
proposing the deletion of code that only *looks* unused because it is referenced dynamically
(Flask routes, console_scripts, subprocesses, string-keyed Telegram dispatch, the `__all__`
re-export shim). Unused *dependencies* are a separate concern (see `dep-auditor` if installed).

## The load-bearing rule

> **The tool flags CANDIDATES, not verdicts.** Never delete a symbol because vulture listed it.
> Every candidate must be confirmed to have no *dynamic* reference before removal, and the
> **`bin/local-env verify` E2E + the 562-test unit suite are the real safety net** — static
> analysis cannot see Flask routing, `getattr` dispatch, or a subprocess invoked by path, but a
> green `verify` + unit run catch what the scan misses. Deleting a dynamically-referenced symbol
> (a route handler, a health-script entry, a Telegram command) imports fine and breaks the running
> system silently.

## Local vs global dead code — use the right tool

- **Local** (unused imports F401, unused locals F841, redefinitions F811) is ALREADY a hard CI
  gate here (`flake8 --max-line-length=120 src/`, enforced since Spec 3, currently at 0). Do not
  re-report it.
- **Global / whole-program** (unused functions, classes, methods, whole modules, unreachable
  branches) is what flake8 does NOT find and what this skill targets, via **vulture**.

## Tool: vulture (dev-only)

`vulture` is the whole-program reachability tool for Python. It is a **dev-only** dependency
(declared in `tests/requirements.txt`, never in `pyproject.toml` runtime deps). Run it through the
repeatable runner so the allowlist and threshold are always applied:

```bash
scripts/find-dead-code.sh            # scan src/ at the default confidence (60)
scripts/find-dead-code.sh 80         # higher-signal only
scripts/find-dead-code.sh --baseline # regenerate the allowlist baseline (review before committing)
```

The runner passes `src/vpn_sentinel/` plus `.vulture_allowlist.py` (the curated false-positive
allowlist) to vulture. Tune the minimum confidence to trade recall for signal.

## Dynamic-reference categories (the false positives — confirm before deleting)

These look unused to vulture but are load-bearing in VPNSentinel:

| Pattern | Where | Why it is referenced dynamically |
|---|---|---|
| Flask route handlers | `api_routes.py`, `dashboard_routes.py`, `health_routes.py` (`@*_app.route(...)`) | dispatched by Flask by URL path, never called by name |
| Entry points | `vpn_sentinel.server.__main__:main`, `vpn_sentinel.client.__main__:main` (`[project.scripts]`, `python -m`) | invoked by the console_script / `-m`, not by an internal caller |
| Health subprocesses | `src/vpn_sentinel/common/health_scripts/*.py` (`healthcheck.py`, `health_monitor.py`, `health_monitor_wrapper.py`) | run as separate processes by path (Docker HEALTHCHECK, the client's health monitor), not imported |
| Public re-exports | `health_scripts/health_common_shim.py` (`print_json`, kept with `# noqa: F401  # re-export`) | re-exported for consumers; "no internal caller" does NOT mean dead |
| Telegram command handlers | `telegram_commands.py` (`handle_status`, `handle_ping`, `handle_start`, ...) | selected by command text (string-keyed dispatch), not called directly |
| Daemon thread targets | `api_routes.cleanup_stale_clients`, Telegram polling loop, the per-app `run_flask_app` targets | passed as `threading.Thread(target=...)`, never called by name |
| Telegram / geolocation fallbacks | `telegram.py`, `geolocation.py`, `network.py` | provider-cascade fallbacks invoked conditionally |
| pytest test_* + fixtures | `tests/` | collected and invoked by pytest, not by the package |

When vulture flags one of these, it is a **false positive** — add it to `.vulture_allowlist.py`
with a one-line *why*, do not delete it.

## Two detection modes

1. **Static (default).** `scripts/find-dead-code.sh` — vulture whole-program scan. Fast; finds most
   unreferenced symbols.
2. **Coverage (complementary).** Code vulture says is reachable but that has **0 unit coverage** is
   a strong dead lead — cross-check against `--cov=vpn_sentinel.common` (the gate runs at ~84%).
   Caveat: low coverage alone is not dead (it may be untested-but-used, e.g. integration-only or
   the entry points, which are 0% in unit but exercised by `bin/local-env verify`). Confirm before
   acting.

## Workflow

1. **Baseline first.** Run `scripts/find-dead-code.sh --baseline` once to capture the current
   findings into `.vulture_allowlist.py`; review it, prune obvious dynamic-refs, commit it. Then
   only ACT on *new* findings — incremental, not a one-shot mass cleanup.
2. **Run** at a high-signal threshold; group output by confidence.
3. **Verify each candidate** before believing it: `grep` the name across `src/` + `tests/`
   (including string literals, `@app.route`, `target=`, `__all__`, `[project.scripts]`), check the
   table above, and whether it is referenced only in tests (test-only = effectively dead, but
   confirm it was not an intended public helper).
4. **Classify:**
   - **Confirmed dead** -> remove in a small, single-purpose commit; then run
     `python -m pytest tests/unit/` AND `bin/local-env verify` (both must stay green).
   - **Dynamically referenced (false positive)** -> add to `.vulture_allowlist.py` with a one-line
     *why*, so the scan gets quieter and more trustworthy over time.
   - **Unsure** -> keep it; open a ticket. Bias toward keeping.
5. **Respect project invariants.** Never remove a symbol `CLAUDE.md` or `.claude/skills/vpnsentinel`
   marks as load-bearing (e.g. the in-memory `client_status`, the geolocation/DNS fallbacks) on
   vulture's say-so.

## Output format

Group findings into **High-confidence dead** / **Likely dead (verify dynamic refs)** / **Probable
false positives** (anything matching a dynamic category above). For each, give
`file:line — symbol (kind, confidence)` plus a one-line verification note. **Never auto-delete** —
propose removals for confirmation, or file gate-ready tickets for non-trivial cleanups.

## Scope boundary

This owns **source** dead code. Unused **dependencies** are a separate concern (the dependency
upgrades and `dep-auditor` pattern) — do not double-report them here.
