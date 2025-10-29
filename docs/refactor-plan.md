## 🧭 VPNSentinel Refactor Intent & Long-Term Plan

**Repository:** [VPNSentinel](https://github.com/agigante80/VPNSentinel) **Primary branch for
refactor work:** `refactor/unified-architecture` **Environment:** Visual Studio Code

---

### 🎯 **Objective**

The purpose of this refactor is to **modernize, modularize, and stabilize** the VPNSentinel
codebase. The main focus is on the **server** (`vpn-sentinel-server/vpn-sentinel-server.py`) —
introducing a **robust, standardized health-monitor and healthcheck** system, similar in structure
and reliability to what’s implemented on the **client** (`vpn-sentinel-client/`).

At the same time, this initiative aims to:

* **Unify and centralize shared logic** (logging, configuration, geolocation, networking, health). *
  **Reduce duplication** between the server and client. * **Gradually migrate** high-value shell-
  based logic to Python. * **Preserve stability** via small, testable, incremental PRs. *
  **Encourage architectural consistency** across all VPNSentinel components.

Refactoring the **client side** is **welcome and encouraged** whenever it improves shared
functionality, reduces duplication, or enhances maintainability.

> ✅ You have full freedom to **rename, move, delete, or reorganize files and directories** if it
> contributes to a cleaner, more maintainable, and future-proof architecture.

---

### 💡 **Context & Current State**

* The repo mixes **Python (server)** and **shell (client)**. * Client-side code already includes
  valuable logic (e.g., geolocation, health, network checks) that should be reused. * Shared shell
  libraries (e.g., `lib/health-common.sh`) overlap with emerging Python modules. * The
  `vpn_sentinel_common` package has been added under `vpn_sentinel_common/` and already contains:

* `logging.py` (logging helpers) and `geolocation.py` (geolocation helper). * A lightweight `vpn-
  sentinel-server/health-monitor.py` that uses `vpn_sentinel_common.logging` for consistent logs. *
  Tests and smoke scripts that exercise the health monitor and server behavior (see `tests/` and
  `scripts/smoke/`).

Moving forward, the **active refactor branch is `refactor/unified-architecture`** — use this branch
for consolidated refactor PRs.

---

### 🧱 **Long-Term Goals**

1. **Centralize shared logic** in a Python package: `vpn_sentinel_common/` (logging, config,
geolocation, network, health, monitor, etc.). 2. **Modularize the server** into a structured Python
package (`vpn_sentinel_server/`). 3. **Refactor the client** as needed to reuse shared Python
modules. 4. **Standardize health endpoints** for all components:

* `/health` * `/health/ready` * `/health/startup` 5. **Ensure all PRs remain small, safe, and well-
  tested**. 6. **Maintain backward compatibility** until the Python versions fully replace the shell
  logic. 7. **Adopt strong CI, linting, and type-checking practices**.

---

### ⚙️ **Critical Considerations**

* **Gradual migration:** Port key shell logic to Python in stages — starting with high-value modules
  like geolocation and health monitoring. * **Robust CI:**

* Use `pip install -e .` for editable installs of `vpn_sentinel_common`. * Keep all tests green in
  CI. * Introduce integration smoke runs using Docker. * **Consistency in behavior:** Match existing
  shell logic behavior during migration (write regression tests). * **Freedom to restructure:**
  Move, rename, or remove files freely to create clean boundaries between modules.

---

### 🪜 **Incremental PR Roadmap**

All refactor work occurs under the **`refactor/unified-architecture`** branch, in small, reviewable
steps.

| PR     | Focus                 | Description
| | ------ | --------------------- | ---------------------------------------------------------------
----------------------------------------------------------------------------------------------------
---- | | **1**  | ✅ Done                | Added `vpn_sentinel_common/logging`, initial `vpn-
sentinel-server/health-monitor.py`, and client-side shim `vpn-sentinel-client/lib/geo_client.py`.
Basic smoke tests exercise these components. | | **2**  | In progress           | Packaging: create
`pyproject.toml` / `setup.cfg` to make `vpn_sentinel_common` installable as an editable package.
(NOT YET PRESENT in repo).                            | | **3**  | ✅ Done                |
Geolocation: `vpn_sentinel_common/geolocation.py` implemented and consumed by `vpn-sentinel-client`
shim.                                                                | | **4**  | Not started
| Shared health: design and add `vpn_sentinel_common/health.py` with a final JSON schema for
`/health` endpoints and helper functions.                                     | | **5**  | In
progress           | Server modularization: server remains as `vpn-sentinel-server/vpn-sentinel-
server.py` (single-file) — plan is to refactor into `vpn_sentinel_server/` package and split
responsibilities. | | **6**  | Not started           | Shared monitor: consider moving monitor logic
from `vpn-sentinel-server/health-monitor.py` into `vpn_sentinel_common.monitor` for reuse by client
and server.           | | **7**  | In progress           | Migrate shell helpers: `vpn-sentinel-
client/lib/geo_client.py` shows a small shim; `lib/health-common.sh` still exists and should be
ported gradually.                     | | **8**  | Not started           | Typing & Linting: CI
already runs `flake8`/`black` checks and unit tests; add `mypy` and `ruff` gradually and enforce in
CI.                                                | | **9**  | ✅ Done                | Integration
CI: GitHub Actions already runs unit and integration flows, Docker build tests, and docker-compose-
based integration smoke tests (see `.github/workflows/ci-cd.yml`). | | **10** | Ongoing
| Cleanup & Docs: update README, tests, and developer docs as components migrate; only remove shell
scripts after Python replacements are validated by tests and smoke runs.    |

---

### 🧩 **Target Architecture**

```
vpn_sentinel_common/
 ├── __init__.py
 ├── logging.py        # implemented
 ├── geolocation.py    # implemented
 ├── (planned)
 ├── config.py         # future
 ├── health.py         # future (shared health schema)
 ├── network.py        # future
 ├── monitor.py        # future (shared monitor)
 ├── pidfile.py        # future
 └── types.py          # future

vpn_sentinel_server/
 ├── __init__.py
 ├── api.py
 ├── health.py
 ├── dashboard.py
 ├── telegram.py
 ├── config.py
 └── main.py

vpn_sentinel_client/
 ├── vpn-sentinel-client.sh      # thin wrapper (legacy)
 ├── lib/
 │    ├── geo_client.py           # shim that imports vpn_sentinel_common.geolocation
 │    ├── (other legacy shell helpers — gradually ported)
 └── (client should progressively import `vpn_sentinel_common` for shared logic)
```

---

### 🧠 **Decision Points**

* Confirm that **`feature/server-refactor`** is now the main long-term branch (replacing
  `refactor/vpn-sentinel-common`). * Decide the **next actionable step**:

* **PR 2** → Packaging (`vpn_sentinel_common` installable, editable CI) * **PR 3** → Geolocation
  extraction (client/server reuse) * Establish the **final JSON schema** for `/health` endpoints
  before shared implementation. * As code evolves, make structural changes (file renames, folder
  moves, or deletions) freely — clarity and maintainability come first.

---

### ✅ **Summary**

> The VPNSentinel refactor will unify server and client around a shared Python foundation
> (`vpn_sentinel_common`), improving health monitoring, observability, and maintainability. > > All
> work proceeds under the `feature/server-refactor` branch. > > The developer has **full freedom**
> to **rename, move, delete, or restructure files** wherever it leads to a cleaner, more robust
> architecture. > > Refactoring the **client side** is fully encouraged whenever it strengthens
> shared logic or reduces duplication.

---

## Contributing: branch & PR conventions

This file is the single source-of-truth for the refactor. Any change of direction should update it
first.

- Active refactor branch: `refactor/unified-architecture`. Create topic branches off this branch and
  target PRs against it. - Topic branch naming: `refactor/<area>-<short-desc>` or `feature/<short-
  desc>` for small improvements. Examples: - `refactor/server-modularization` - `refactor/packaging-
  vpn-sentinel-common` - `feature/geolocation-mocks` - Keep PRs small and focused: aim for 200–500
  lines of change when possible.

### PR checklist (must pass before merge into `refactor/unified-architecture`)

1. Run the smoke test locally (quick, pre-merge verification):

```bash
bash scripts/smoke/run_local_smoke.sh
```

- The smoke script runs the project in a lightweight environment and validates basic endpoints
  (dashboard, health endpoints). Run it on your machine before raising a PR to catch obvious
  regressions.

2. Run the full test suite locally, including ALL integration tests (including those that require
Docker):

```bash
# Ensure Docker is running for integration tests that require containers
./tests/run_tests.sh --all
```

- Some server-dependent integration tests are skipped by default and require setting
  `VPN_SENTINEL_SERVER_TESTS=1` in the environment (see `tests/integration_server/` README). When
  running `--all`, ensure Docker is available and that you enable server-dependent tests if you
  intend to validate the full server stack.

3. All unit tests pass locally and in CI. Use `./tests/run_tests.sh --unit`. 4. If touching runtime
code, add or update unit tests and integration smoke tests as appropriate. 5. Linting: fix
`flake8`/`black` issues. New style checks (e.g., `ruff`, `mypy`) should be added behind a follow-up
PR. 6. CI configuration: ensure `.github/workflows/ci-cd.yml` still runs without errors for the PR.
7. Documentation: update `docs/refactor-plan.md`, `README.md` or deployment `README` if behavior or
configuration changes. 8. No secrets or credentials in commits.

### Naming and package conventions

- Python packages use snake_case directories (e.g., `vpn_sentinel_common`, `vpn_sentinel_server`). -
  Public functions/classes should be typed (gradual typing is ok) and documented with a one-line
  docstring. - Environment variables use UPPER_SNAKE_CASE and begin with `VPN_SENTINEL_`. -
  CLI/script entrypoints should live in component folders and remain runnable without installing the
  package (tests rely on this behaviour).

## Immediate next steps (short-term roadmap)

1. Add `pyproject.toml` for `vpn_sentinel_common` (editable install). This should be a small PR that
only adds packaging metadata and CI install step. 2. Implement `vpn_sentinel_common/health.py` and
finalise `/health` JSON schema. Add unit tests validating schema shape and endpoints. 3. Split `vpn-
sentinel-server/vpn-sentinel-server.py` into `vpn_sentinel_server/` package (API, health, dashboard,
config, main). Keep behaviour identical and add tests during the split. 4. Consolidate monitor code
into `vpn_sentinel_common.monitor` or keep the server monitor as a thin wrapper that imports shared
monitor code. 5. Begin incremental port of `lib/health-common.sh` and other shell helpers to Python,
keeping thin shell wrappers until parity is verified.

## Maintenance notes

- Keep `docs/refactor-plan.md` up to date. Any change in architecture, branch naming, or major
  decision must be recorded here. - When a component is fully ported to Python and validated by CI,
  remove its shell counterparts in a separate cleanup PR. - Prefer small, reversible PRs. If a PR
  becomes large, split it into a behavior-preserving first PR and follow-up refactors that change
  structure.

