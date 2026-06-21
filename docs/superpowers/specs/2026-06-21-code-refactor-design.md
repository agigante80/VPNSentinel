# Design: Spec 3 — Code Refactor (Format/Lint Cleanup + Thread Safety)

- **Date:** 2026-06-21
- **Status:** Approved (design); pending implementation plan
- **Author:** Claude (with agigante80)
- **Scope:** Two cohesive parts: **(A)** format the codebase with `black`, clear the ~394 lint
  violations to zero, and make CI enforce it going forward (plus a one-line dead-`PYTHONPATH`
  cleanup); **(B)** make the shared `client_status` dict thread-safe with a lock.
  Guarded throughout by the 560-test unit suite and `bin/local-env verify`.

## Non-Goals (deferred follow-ups)
- **Spec 3b:** split the 919-line `dashboard_routes.py` monolith (extract templates/static).
- **Spec 3c:** complete type hints + add mypy to CI.
- No functional/behavioral changes beyond the thread-safety fix; `black` is formatting-only
  (AST-preserving), and the residual lint fixes are behavior-preserving (with one documented caveat
  on bare-`except`).

## Decisions (locked during brainstorming)
1. Formatter: **`black`** (already in `tests/requirements.txt`), `line-length = 120` to match the
   existing flake8 convention.
2. Format scope: **`src/` + `tests/`**.
3. Enforce via pre-commit (`black`) and a **real** CI gate (`black --check` + `flake8` that fail).
4. Thread safety: a module-level `threading.Lock` guarding all `client_status` access.
5. Fold in the cosmetic dead `PYTHONPATH=/app` removal from the server runtime Dockerfile.

## Part A — Format + lint cleanup, then enforce

Current state: `flake8 --max-line-length=120 src/` reports **394 violations** (CI runs only the
syntax subset `E9,F63,F7,F82` with `continue-on-error: true`, so full style is unenforced). Breakdown:
W293 ×195, E111 ×76, W191 ×42 (tabs — only `security.py`), E501 ×14, E114 ×12, W291 ×11, F401 ×10,
W292 ×8, E722 ×4, E402 ×4, E302 ×4, E128 ×4, F841 ×3, E305 ×3, F541 ×2.

### A1. Run black
- Add to `pyproject.toml`:
  ```toml
  [tool.black]
  line-length = 120
  target-version = ["py312"]
  ```
- Run `black src/ tests/`. black fixes the whitespace/blank-line/indentation bulk
  (W293, W291, W292, W191 tabs→spaces in `security.py`, E111, E114, E128, E302, E305) by reformatting.
  black does NOT fix: F401, F841, F541, E402, E722, or E501 on unbreakable strings/URLs — those are
  handled by hand in A2.

### A2. Residual fixes black does not make
After black, fix the remaining real violations by hand (re-run flake8 to get the live list):
- **F401** unused imports → remove (verify the name is truly unused, not re-exported).
- **F841** unused local variables → remove or prefix `_`.
- **F541** f-string without placeholders → drop the `f` prefix.
- **E402** module import not at top → move to top, unless intentionally after a `sys.path` setup
  (then `# noqa: E402` with a one-line reason).
- **E722** bare `except:` → `except Exception:`. **Caveat:** bare `except` also catches
  `KeyboardInterrupt`/`SystemExit`; at each of the 4 sites, confirm catching only `Exception` is the
  intent (it is for the geolocation/DNS/Telegram fallback sites). If a site intentionally swallows
  Ctrl-C, keep it explicit with `except (Exception, KeyboardInterrupt):` and a comment — do not
  silently change that behavior.
- **E501** long lines black cannot break (long string literals / URLs) → wrap if reasonable,
  else `# noqa: E501` with a reason.

Target: `flake8 --max-line-length=120 src/` and `black --check src/ tests/` both clean.

### A3. Enforce going forward
- `.pre-commit-config.yaml`: add the `black` hook (psf/black) alongside the existing shfmt/hooks.
- `.github/workflows/ci-cd.yml` lint job: replace the lenient flake8 (`continue-on-error: true`,
  syntax-subset) with **hard gates** that fail the build:
  - `black --check src/ tests/`
  - `flake8 --max-line-length=120 src/`
  Keep the `pylint` step advisory (`continue-on-error: true`) — pylint is noisier and out of scope to
  gate here.

### A4. Fold-in: dead PYTHONPATH
- Remove the now-dead `PYTHONPATH=/app` / `ENV PYTHONPATH=...` line from the server runtime
  Dockerfile (`src/vpn_sentinel/server/Dockerfile`) — the non-editable install puts the package in
  site-packages, so `/app` on PYTHONPATH does nothing. Guarded by `bin/local-env verify`.

## Part B — Thread-safety: lock `client_status`

`client_status` (`src/vpn_sentinel/common/api_routes.py:18`) is a module-level dict mutated by the
keepalive handler and the background cleanup thread, and read by `/status` and the dashboard — across
3+ threads with **no synchronization**. Concrete races: a `del client_status[client_id]` in cleanup
while `/status` iterates; concurrent keepalive writes.

### B1. Add the lock
- `client_status_lock = threading.Lock()` at module scope next to `client_status`.
- Guard every access with `with client_status_lock:` — narrowly, around the dict operation only,
  **never held during slow I/O** (Telegram sends, geolocation HTTP). Sites:
  - keepalive: the `old_ip` read (`:172`) and the `client_status[client_id] = {...}` write (`:179`)
    — read+compute the status under the lock, release before any Telegram/network call.
  - `/status` handler (`:117`): snapshot `dict(client_status)` under the lock, then `jsonify` the copy
    (prevents "dictionary changed size during iteration").
  - cleanup thread (`:248`–`:291`): guard the `if not client_status`, the `list(client_status.items())`
    iteration, and each `del client_status[client_id]`.
  - any dashboard read of `client_status` → snapshot a copy under the lock.
- Single, non-nested lock (no lock acquired while holding another) → no deadlock.

### B2. Test
- Add a focused unit test (e.g. `tests/unit/test_api_routes_concurrency.py`) that spins up N threads
  hammering keepalive writes while another thread runs the cleanup/iteration, asserting no exception
  and a consistent final state. Use a short, deterministic loop (not timing-dependent flakiness).
- Existing tests must stay green (560/92).

## Verification strategy (per task)
- `python -m pytest tests/unit/ -q` → 560 passed / 92 skipped (plus the new concurrency test).
- `black --check src/ tests/` → clean; `flake8 --max-line-length=120 src/` → 0.
- `bin/local-env verify` → green 23/23 (rebuilds images — catches any Dockerfile/PYTHONPATH issue).
- `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci-cd.yml'))"` → valid.
- The coverage gate (`--cov=vpn_sentinel.common --cov-fail-under=80`) must stay ≥80%.

## Risks
- **black reformatting is large but safe** (AST-preserving). The big diff is expected; review focuses
  on the non-black residual fixes.
- **Bare-`except` change** could alter Ctrl-C/SystemExit behavior — handled per-site in A2.
- **Lock scope**: holding the lock during network I/O would serialize requests / risk slow handlers.
  Mitigation: guard only the dict ops; copy-then-release before I/O.
- **CI hard-gating**: once flake8/black gate, any new violation fails CI — intended, but confirm the
  cleanup truly reaches 0 first.

## Acceptance criteria
- `black --check src/ tests/` clean; `flake8 --max-line-length=120 src/` = 0 violations.
- `[tool.black]` in pyproject (line-length 120); `black` in pre-commit; CI flake8+black gate is hard
  (no `continue-on-error`).
- `client_status` access is lock-guarded everywhere; a concurrency test passes; no lock held during
  network I/O.
- Dead `PYTHONPATH=/app` removed from the server Dockerfile.
- `bin/local-env verify` green 23/23; unit 560/92 (+ new test); coverage ≥80%; CI YAML valid.
- No behavior change except the thread-safety fix.

## Follow-on
- Spec 3b: split `dashboard_routes.py`. Spec 3c: type hints + mypy.
