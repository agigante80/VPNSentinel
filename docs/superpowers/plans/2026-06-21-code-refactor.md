# Spec 3 Code Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Format the codebase with `black`, drive the ~394 lint violations to zero and enforce it in CI, and make the shared `client_status` dict thread-safe — with no behavior change beyond the thread-safety fix.

**Architecture:** Four sequential tasks: (1) `black` reformat, (2) hand-fix the residual real lint issues, (3) add a `threading.Lock` around `client_status`, (4) turn on the CI/pre-commit gates and remove a dead `PYTHONPATH`. Each ends green on the unit suite and, where Docker is touched, `bin/local-env verify`.

**Tech Stack:** Python 3.12, black (already in `tests/requirements.txt`), flake8, pre-commit, pytest, Docker.

## Global Constraints

- Branch: `develop`. Commit after each task. End every commit message with:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- Baselines: `python -m pytest tests/unit/ -q` → **560 passed / 92 skipped** (becomes **562 / 92**
  after the 2 new concurrency tests in Task 3), exit 0. `bin/local-env verify` → **23/23** green, exit 0, no
  leftover containers. Coverage gate `--cov=vpn_sentinel.common --cov-fail-under=80` must stay ≥80%.
- black config: `line-length = 120`, `target-version = ["py312"]`. Format scope: `src/` + `tests/`.
- No behavior change except the thread-safety fix. black is AST-preserving; residual fixes are
  behavior-preserving (bare-`except` change handled per-site).
- No absolute `/home/$USER` paths. Image names unchanged.

---

### Task 1: Apply black to src/ and tests/

**Files:**
- Modify: `pyproject.toml` (add `[tool.black]`)
- Modify: all `*.py` under `src/` and `tests/` (reformatted by black)

**Interfaces:**
- Produces: a black-formatted tree; `black --check src/ tests/` clean. Later tasks edit already-formatted files.

- [ ] **Step 1: Confirm black is available**

```bash
python3 -m black --version || pip install 'black>=23.0.0'
```
Expected: prints a black version (it's in `tests/requirements.txt`).

- [ ] **Step 2: Add black config to pyproject.toml**

Append to `pyproject.toml`:
```toml
[tool.black]
line-length = 120
target-version = ["py312"]
```

- [ ] **Step 3: Record the pre-format violation count (for the report)**

```bash
flake8 --max-line-length=120 src/ --count 2>/dev/null | tail -1
```
Expected: ~394.

- [ ] **Step 4: Run black**

```bash
python3 -m black --line-length 120 src/ tests/
```
Expected: black reports "reformatted N files". This is a large diff — expected.

- [ ] **Step 5: Verify formatting is stable and tests still pass**

```bash
python3 -m black --check src/ tests/ && echo "black clean"
python -m pytest tests/unit/ -q 2>&1 | tail -2
```
Expected: "black clean"; unit suite `560 passed, 92 skipped`, exit 0 (black is AST-preserving — no test should change).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "style: format src/ and tests/ with black (line-length 120)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Fix the residual flake8 violations black cannot

**Files (modify):** `src/vpn_sentinel/common/config.py`, `dashboard_routes.py`, `geolocation.py`,
`health.py`, `health_routes.py`, `server_utils.py`,
`health_scripts/health_monitor.py`, `health_scripts/health_monitor_wrapper.py`,
`health_scripts/health_common_shim.py` — plus any others a fresh `flake8` run reports.

**Interfaces:**
- Produces: `flake8 --max-line-length=120 src/` = 0 violations.

- [ ] **Step 1: Get the live residual list (black may have shifted line numbers)**

```bash
flake8 --max-line-length=120 src/ 2>/dev/null | sed -E 's/:[0-9]+:[0-9]+:/:/' | sort | uniq -c | sort -rn
flake8 --max-line-length=120 src/ 2>/dev/null
```
Expected: only non-formatting codes remain (F401, F841, F541, E402, E722, E501). Use the second
command's exact file:line list to drive the fixes.

- [ ] **Step 2: Remove unused imports (F401)**

Known sites (re-confirm against Step 1): `config.py` (`os`, `time`), `dashboard_routes.py` (`sys`,
`io.StringIO`), `geolocation.py` (`socket`), `health.py` (`shutil`), `health_routes.py`
(`.log_utils.log_info`, `os`), `health_scripts/health_monitor.py` (`urllib.parse.parse_qs`).
Delete each unused import line.
**Caveat — shim re-exports:** `health_scripts/health_common_shim.py:9` imports
`...healthcheck.print_json`. A `*_shim.py` may import a name purely to re-export it. If so, add the
name to a module `__all__` (or `# noqa: F401  # re-export`) instead of deleting. Confirm whether
anything imports `print_json` from the shim (`grep -rn "print_json" src/ tests/`); delete only if
truly unused.

- [ ] **Step 3: Fix unused locals (F841)**

`health_scripts/health_monitor.py:~77`, `health_scripts/health_monitor_wrapper.py:~132,~140`: these
are `except SomeError as e:` where `e` is never used. Change to `except SomeError:` (drop `as e`).
Verify the body does not reference `e`.

- [ ] **Step 4: Fix bare excepts (E722)**

Sites: `dashboard_routes.py:~105`, `health_scripts/health_monitor.py:~112`, `server_utils.py:~68`,
`server_utils.py:~88`. Change `except:` → `except Exception:`.
**Behavioral caveat:** bare `except` also catches `KeyboardInterrupt`/`SystemExit`. Read each site:
all four are fallback/degradation handlers (server-util port binding, health-monitor loop, dashboard
render) where catching only `Exception` is correct. If any site is a top-level loop meant to survive
Ctrl-C deliberately, use `except (Exception, KeyboardInterrupt):` with a one-line comment instead of
silently dropping that behavior.

- [ ] **Step 5: Fix any residual F541 / E402 / E501**

- F541 (f-string with no placeholder): drop the `f` prefix.
- E402 (import not at top): move to the top of the module, unless it follows a deliberate `sys.path`
  setup — then keep it and add `# noqa: E402  # after sys.path bootstrap`.
- E501 (line > 120 black could not break — long string/URL): wrap if natural, else append
  `# noqa: E501  # <short reason>`.

- [ ] **Step 6: Verify flake8 is clean and tests pass**

```bash
flake8 --max-line-length=120 src/ --count 2>&1 | tail -1
python -m pytest tests/unit/ -q 2>&1 | tail -2
```
Expected: `0` flake8 violations; unit `560 passed, 93 skipped`.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "style: clear residual flake8 violations (unused imports, bare excepts, unused vars)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Make client_status thread-safe

**Files:**
- Modify: `src/vpn_sentinel/common/api_routes.py`
- Create: `tests/unit/test_api_routes_concurrency.py`

**Interfaces:**
- Consumes: the module-level `client_status` dict in `api_routes.py`.
- Produces: `client_status_lock = threading.Lock()` (module-level, importable for the test); all
  `client_status` access guarded.

- [ ] **Step 1: Write the failing concurrency test**

Create `tests/unit/test_api_routes_concurrency.py`:

```python
"""Concurrency safety for the shared client_status dict.

Without a lock, iterating client_status while another thread mutates it raises
RuntimeError('dictionary changed size during iteration'). The lock must prevent that.
"""
import threading

import pytest

from vpn_sentinel.common import api_routes


@pytest.mark.unit
def test_client_status_lock_exists():
    assert isinstance(api_routes.client_status_lock, type(threading.Lock()))


@pytest.mark.unit
def test_concurrent_mutation_and_iteration_is_safe():
    api_routes.client_status.clear()
    errors = []
    stop = threading.Event()

    def writer():
        i = 0
        while not stop.is_set():
            with api_routes.client_status_lock:
                api_routes.client_status[f"c{i % 50}"] = {"ip": "1.2.3.4", "last_seen": i}
            i += 1

    def reader():
        try:
            for _ in range(2000):
                with api_routes.client_status_lock:
                    # snapshot under the lock, then "use" outside
                    snapshot = dict(api_routes.client_status)
                _ = list(snapshot.items())
        except RuntimeError as exc:  # pragma: no cover - this is the bug we prevent
            errors.append(exc)
        finally:
            stop.set()

    ts = [threading.Thread(target=writer) for _ in range(4)] + [threading.Thread(target=reader)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(timeout=10)
    api_routes.client_status.clear()
    assert errors == [], f"thread-safety violation: {errors}"
```

- [ ] **Step 2: Run it — expect failure (no lock yet)**

```bash
python -m pytest tests/unit/test_api_routes_concurrency.py -v --no-cov 2>&1 | tail -10
```
Expected: `test_client_status_lock_exists` FAILS with `AttributeError: module ... has no attribute
'client_status_lock'`.

- [ ] **Step 3: Add the lock and guard every access in api_routes.py**

In `src/vpn_sentinel/common/api_routes.py`:
- Ensure `import threading` is present (add if missing).
- Right after `client_status = {}` (currently `:18`), add:
  ```python
  client_status_lock = threading.Lock()
  ```
- Guard each access — wrap ONLY the dict operation; do NOT hold the lock during Telegram/HTTP I/O:
  - The keepalive handler's `old_ip = client_status.get(...)` read and the
    `client_status[client_id] = {...}` write: perform the read, compute the new record, and assign
    inside a single `with client_status_lock:` block; then exit the block BEFORE any Telegram send or
    geolocation/network call.
  - The `/status` handler (`return jsonify(client_status)`): change to
    ```python
    with client_status_lock:
        snapshot = dict(client_status)
    return jsonify(snapshot)
    ```
  - The cleanup function (`cleanup_stale_clients`): wrap the `if not client_status` check, the
    `list(client_status.items())` iteration, and each `del client_status[client_id]` in
    `with client_status_lock:`. If the loop body does network/Telegram work per stale client, collect
    the stale ids under the lock first, then do the I/O outside the lock, then re-acquire the lock to
    `del`. Keep the lock held only around dict ops.
- Any dashboard read of `client_status` in this module: snapshot a copy under the lock.

- [ ] **Step 4: Run the concurrency test + full unit suite**

```bash
python -m pytest tests/unit/test_api_routes_concurrency.py -v --no-cov 2>&1 | tail -6
python -m pytest tests/unit/ -q 2>&1 | tail -2
```
Expected: both concurrency tests PASS; unit suite `562 passed, 92 skipped` (the +2 are the new tests;
confirm the skipped count is unchanged at 92 and only passed grew, by 2).

- [ ] **Step 5: flake8 the changed file + verify the live stack**

```bash
flake8 --max-line-length=120 src/vpn_sentinel/common/api_routes.py
bin/local-env verify
```
Expected: flake8 clean; `bin/local-env verify` green 23/23, exit 0 (the server container exercises the
guarded keepalive/status paths end-to-end).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "fix(api): guard shared client_status with a lock (thread safety) + concurrency test

client_status is mutated by the keepalive handler and cleanup thread and read by
/status + dashboard across 3+ threads. Add a threading.Lock guarding all dict ops
(copy-then-release before any network/Telegram I/O). Adds a concurrency regression test.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Enforce gating in CI + pre-commit; remove dead PYTHONPATH

**Files:**
- Modify: `.pre-commit-config.yaml` (add black hook)
- Modify: `.github/workflows/ci-cd.yml` (hard flake8 + black gate)
- Modify: `src/vpn_sentinel/server/Dockerfile` (remove dead `PYTHONPATH`)

**Interfaces:**
- Consumes: a clean tree (Tasks 1–3). Produces: failing CI on any future style violation.

- [ ] **Step 1: Add the black hook to pre-commit**

In `.pre-commit-config.yaml`, append a new repo entry (keep the existing shfmt + pre-commit-hooks
blocks):
```yaml
  - repo: https://github.com/psf/black
    rev: 24.10.0
    hooks:
      - id: black
        args: ["--line-length", "120"]
        files: ^(src|tests)/.*\.py$
```

- [ ] **Step 2: Make the CI lint job a hard gate**

In `.github/workflows/ci-cd.yml`:
- The "Install linting dependencies" step: change `pip install flake8 pylint` →
  `pip install flake8 pylint black`.
- Replace the "Run flake8" step (currently `continue-on-error: true`, `--select=E9,F63,F7,F82`) with a
  hard gate (NO `continue-on-error`):
  ```yaml
      - name: Run black --check
        run: black --check --line-length 120 src/ tests/

      - name: Run flake8
        run: flake8 --max-line-length=120 src/ --count --show-source --statistics --exclude=__pycache__,*.pyc,venv,htmlcov,.git
  ```
- Leave the "Run pylint" step as-is (`continue-on-error: true`) — pylint stays advisory.

- [ ] **Step 3: Remove the dead PYTHONPATH from the server Dockerfile**

In `src/vpn_sentinel/server/Dockerfile`, delete line `ENV PYTHONPATH="/app"` (the non-editable install
puts the package in site-packages; `/app` on PYTHONPATH is dead).

- [ ] **Step 4: Validate config + gates pass on the now-clean tree**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci-cd.yml')); print('ci yaml ok')"
python3 -c "import yaml; yaml.safe_load(open('.pre-commit-config.yaml')); print('precommit yaml ok')"
black --check --line-length 120 src/ tests/ && echo "black clean"
flake8 --max-line-length=120 src/ --count 2>&1 | tail -1
```
Expected: both YAML ok; "black clean"; flake8 `0`.

- [ ] **Step 5: Rebuild + verify (the Dockerfile changed)**

```bash
bin/local-env verify
```
Expected: green 23/23, exit 0, no containers left (the server image rebuilds without the dead
PYTHONPATH and still runs).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "ci: enforce black + flake8 as hard gates; add black pre-commit hook; drop dead PYTHONPATH

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- A1 black + `[tool.black]` → Task 1. A2 residual fixes (F401/F841/F541/E402/E722/E501) → Task 2.
- A3 enforce (pre-commit black + CI hard gate) → Task 4. A4 dead PYTHONPATH → Task 4.
- B1 lock + guards (keepalive/status/cleanup/dashboard) → Task 3. B2 concurrency test → Task 3.
- Verification (unit, black --check, flake8 0, verify, coverage ≥80%, CI yaml) → present in each gate.
- Out of scope (dashboard split, mypy) → not in any task; noted as follow-ups.

**Placeholder scan:** No TBD/TODO. The residual-fix sites are given concretely AND re-derived live in
Task 2 Step 1 (black shifts line numbers). The lock-guard sites are enumerated by responsibility with
the copy-then-release rule; the concurrency test is complete code.

**Consistency:** `client_status_lock` (the name the test imports) is the exact symbol Task 3 Step 3
creates. black line-length 120 is identical in pyproject (Task 1), pre-commit (Task 4), and CI (Task 4).
Baseline 560/92 → 562/92 after the two new tests is stated consistently.

## Out of scope (follow-ups)
- Spec 3b: split `dashboard_routes.py` (919 lines). Spec 3c: type hints + mypy.
