## 🧭 VPNSentinel Refactor Intent & Long-Term Plan

**Repository:** [VPNSentinel](https://github.com/agigante80/VPNSentinel)  
**Primary branch for refactor work:** `refactor/unified-architecture`  
**Environment:** Visual Studio Code

---

### 🎯 Objective

Modernize, modularize, and stabilize the VPNSentinel codebase. The main goals are:

- Centralize shared logic into `vpn_sentinel_common` (logging, config, geolocation, network, health, monitor).  
- Modularize the server monolith into `vpn_sentinel_server`.  
- Gradually migrate high-value shell logic in the client to Python, with thin shims ensuring parity.  
- Provide consistent health-check schema and monitoring abstractions across client and server.  
- Preserve runtime stability and backward compatibility during migration.

> ✅ Full freedom to rename, move, delete, or reorganize files and directories as long as it improves maintainability.

---

### 💡 Context & Current State

- Codebase: server is Python (`vpn-sentinel-server`), client is mostly shell (`vpn-sentinel-client`).  
- Shared library: `vpn_sentinel_common/` exists with `logging.py`, `geolocation.py`, `health.py`.  
- Server modularization: `vpn_sentinel_server/` contains `__init__.py`, `validation.py`, `security.py`, `server_info.py`, `telegram.py`, `utils.py`, `logging.py`. Monolith delegates to these modules for backward compatibility.  
- CI & tests: smoke and full test suite run successfully. 171 tests passed, 41 skipped (Linux dev environment). Smoke runner updated to include new packages in the server Docker image.  

Active branch for all refactor work: **`refactor/unified-architecture`** — all PRs must target this branch.

---

### 🧱 Long-Term Goals

1. Centralize shared logic in `vpn_sentinel_common/`.  
2. Modularize the server into `vpn_sentinel_server/`.  
3. Refactor the client to reuse shared Python modules.  
4. Standardize health endpoints for all components: `/health`, `/health/ready`, `/health/startup`.  
5. Keep PRs small, safe, and well-tested.  
6. Maintain backward compatibility until Python replacements fully replace shell logic.  
7. Adopt strong CI, linting, and type-checking practices.

---

### ⚙️ Critical Considerations

- **Gradual migration:** Start with high-value modules (geolocation, health).  
- **Robust CI:**  
  - Use `pip install -e .` for editable installs of `vpn_sentinel_common`.  
  - Keep all tests green in CI.  
  - Introduce integration smoke runs using Docker.  
- **Consistency in behavior:** Ensure Python replacements match legacy shell logic; write regression tests.  
- **Freedom to restructure:** Move, rename, or remove files to create clear module boundaries.

---

### 🪜 Incremental PR Roadmap

All PRs must target **`refactor/unified-architecture`**.

| PR | Focus | Description |
|----|-------|-------------|
| 1  | ✅ Done | Added `vpn_sentinel_common/logging`, initial server `health-monitor.py`, client shim `vpn-sentinel-client/lib/geo_client.py`. Basic smoke tests executed. |
| 2  | In progress — pyproject.toml added | Server modularization: validation and security helpers moved into `vpn_sentinel_server/`. Monolith delegates for backward compatibility. |
| 3  | ✅ Done | Docker images updated to include `vpn_sentinel_server` and `vpn_sentinel_common`. Smoke and integration tests updated. |
| 4  | In progress | Shared health: `vpn_sentinel_common/health.py` implemented. JSON schema under review. Integration with server health endpoints ongoing. |
| 5  | In progress | Server modularization: splitting `vpn-sentinel-server/vpn-sentinel-server.py` into `vpn_sentinel_server/` modules; tests added to preserve behavior. |
| 6  | ✅ Done | Shared monitor: `vpn_sentinel_common/monitor.py` implemented and unit-tested (see `tests/unit/test_monitor.py`). |
| 7  | In progress | Migrate shell helpers: `lib/health-common.sh` and `vpn-sentinel-client/lib/*.sh` gradually ported to Python with shims maintained until parity confirmed. |
| 8  | Not started | Typing & linting: CI runs `flake8`/`black`; plan to add `mypy` and `ruff` behind feature flags. |
| 9  | ✅ Done | Integration CI: GitHub Actions runs unit and integration flows; Docker-based smoke tests in CI (`.github/workflows/ci-cd.yml`). |
| 10 | Ongoing | Cleanup & Docs: update README and developer docs; remove shell code only after Python replacements pass CI and smoke tests. |

---

### 🧩 Target Architecture

```

vpn_sentinel_common/
├── **init**.py
├── logging.py
├── geolocation.py
├── health.py        # in progress
├── config.py        # planned
├── network.py       # planned
├── monitor.py       # planned
├── pidfile.py       # planned
└── types.py         # planned

vpn_sentinel_server/
├── **init**.py
├── api.py
├── health.py
├── dashboard.py
├── telegram.py
├── config.py
└── main.py

vpn_sentinel_client/
├── vpn-sentinel-client.sh
├── lib/
│    ├── geo_client.py
│    ├── config.sh
│    ├── network.sh
│    ├── payload.sh
│    ├── log.sh
│    └── utils.sh
└── progressively import `vpn_sentinel_common` for shared logic

```

---

### 🧠 Contracts / Standards

**`vpn_sentinel_common.health`**
- Returns JSON with keys: `status` (string: `ok`/`degraded`/`fail`), `components` (dict with component statuses).  
- Inputs: optional override parameters for individual checks.  
- Output format stable across client and server.  

Note: historically the docs mentioned a `warn` status; the canonical implementation uses `degraded`. Either term may be considered equivalent for human readers, but the canonical allowed values are `ok`, `degraded`, and `fail`. If you need `warn` for compatibility, consider accepting it as an alias in `vpn_sentinel_common.health` or normalizing inputs at the caller.

**`vpn_sentinel_common.monitor`**
- Start/stop interface.  
- Heartbeat interval configurable.  
- Outputs standardized JSON or log lines.  
- Reusable in both server and client.

Example usage (python):

```python
from vpn_sentinel_common.monitor import Monitor

def print_hb(hb):
    print(hb)

m = Monitor(component="server", interval=10.0, on_heartbeat=print_hb)
m.start()
# ... run for a while
m.stop()
```

Example heartbeat JSON (canonical shape):

```json
{
  "ts": 1690000000.0,
  "component": "server",
  "status": "ok",
  "info": {}
}
```

---

### Migration checklist (partial)

Track migration of shell helpers to Python. Add rows as work progresses.

| Path | Purpose | Migrated? | Target module | Notes |
|------|---------|----------:|---------------|-------|
| `vpn-sentinel-client/lib/geo_client.py` | geolocation shim | ✅ | `vpn_sentinel_common.geolocation` | shim imports common geolocation helper |
| `vpn-sentinel-client/health-monitor.py` | client health server | ✅ | `vpn_sentinel_common.monitor` (future) | Python health monitor present |
| `lib/health-common.sh` | shared shell health helpers | ❌ | `vpn_sentinel_common.health` | planned port; keep shell shim until parity |
| `vpn-sentinel-client/lib/config.sh` | client config parsing | ❌ | `vpn_sentinel_client.config` (planned) | planned gradual port |
| `vpn-sentinel-client/lib/network.sh` | network helpers | ❌ | `vpn_sentinel_client.network` (planned) | planned gradual port |

Add more rows as you port files and link PRs in the Notes column.

---

### 🛡️ Branch & PR Enforcement

- All refactor PRs must **target `refactor/unified-architecture`**.  
- Use branch protection rules or CI checks to reject PRs targeting other branches.  
- Delete old topic branches after merge.  
- Topic branch naming: `refactor/<area>-<short-desc>` or `feature/<short-desc>`.

---

### ✅ Summary

VPNSentinel is being unified around `vpn_sentinel_common`. This improves health monitoring, observability, and maintainability. All work occurs under `refactor/unified-architecture`. Client refactoring is encouraged only if it strengthens shared logic or reduces duplication. Developers have full freedom to rename, move, delete, or restructure files for maintainability.

---

### Immediate Next Steps

1. Finalize `/health` JSON schema in `vpn_sentinel_common/health.py`.  
2. Split `vpn-sentinel-server/vpn-sentinel-server.py` into `vpn_sentinel_server/` modules.  
3. Consolidate monitor code into `vpn_sentinel_common/monitor.py`.  
4. Incrementally port shell helpers (`lib/health-common.sh`, `vpn-sentinel-client/lib/*.sh`) to Python.  
5. Ensure CI runs `pip install -e .` for `vpn_sentinel_common` and passes smoke/integration tests.

---

### Maintenance Notes

- Keep `docs/refactor-plan.md` up to date; any architectural, branch, or major decision change must be recorded.  
- Remove shell counterparts only after Python replacements pass tests and smoke runs.  
- Prefer small, reversible PRs; split large PRs into behavior-preserving first and structural refactors later.  
