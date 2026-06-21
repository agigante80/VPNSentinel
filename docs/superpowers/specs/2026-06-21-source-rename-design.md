# Design: Spec 2b — Source/Package Rename to `src/` Unified Namespace

- **Date:** 2026-06-21
- **Status:** Approved (design); pending implementation plan
- **Author:** Claude (with agigante80)
- **Scope:** Spec 2b of the restructure track. Collapse the hyphenated entry-point dirs and the
  `vpn_sentinel_common` package into one importable `src/vpn_sentinel/` namespace
  (`common`, `server`, `client`). Mechanical rename + import rewrite; **no logic changes** except
  wrapping each entry script's top-level code in a `main()` (required for console_scripts).
  Code refactor of module internals remains **Spec 3**.
- **Guarded by** the Spec 1 safety net: `bin/local-env verify` rebuilds the images from the new
  Dockerfiles and runs the E2E, so it validates imports, packaging, entry points, and Docker
  end-to-end after every task.

## Problem

The package `vpn_sentinel_common` is well-named and importable, but the two deployable units are
hyphenated dirs holding hyphenated entry scripts (`vpn-sentinel-server/vpn-sentinel-server.py`,
`vpn-sentinel-client/vpn-sentinel-client.py`). Hyphenated `.py` files cannot be imported (only run
as scripts), forcing `sys.path.insert` hacks, and the naming is inconsistent
(`vpn-sentinel-*` dirs vs `vpn_sentinel_common` package).

## Goals

- One consistent, importable namespace: `src/vpn_sentinel/{common,server,client}`.
- Entry points runnable as modules (`python -m vpn_sentinel.server`) and as console_scripts
  (`vpn-sentinel-server`).
- Remove the `sys.path` hacks.
- Zero behavior change for end users: **Docker Hub image names stay `agigante80/vpn-sentinel-server`
  and `agigante80/vpn-sentinel-client`**; the E2E and unit suites stay green.

## Non-Goals (deferred)

- **Spec 3:** refactoring the internals of `vpn_sentinel.common` modules.
- Un-skipping the legacy `tests/integration/test_e2e.py` shim (and the `__init__.py` it would then
  require to avoid the `server_dependent/` basename collision — see the Spec 2 ledger note). Spec 2b
  changes no test skips, so that collision stays dormant.

## Decisions (locked during brainstorming)

1. Depth: full `src/` unified namespace (`vpn_sentinel_common` → `vpn_sentinel.common`).
2. Dockerfiles co-located in `src/`: `src/vpn_sentinel/server/Dockerfile`, `.../client/Dockerfile`.
3. Distribution name: `vpn-sentinel` (was `vpn-sentinel-common`).
4. Add `console_scripts` (`vpn-sentinel-server`/`-client`) → requires a `main()` in each entry.
5. One spec; the plan sequences it into ~5 verify-gated tasks.

## Target layout

```
src/
  vpn_sentinel/
    __init__.py
    common/                       # was vpn_sentinel_common/ (21 modules)
      __init__.py
      api_routes.py  config.py  dashboard_routes.py  geolocation.py  health.py
      health_monitor.py  health_routes.py  log_utils.py  monitor.py  network.py
      payload.py  security.py  server.py  server_info.py  server_utils.py
      telegram.py  telegram_commands.py  utils.py  validation.py  version.py
      country_codes.py
      health_scripts/
        healthcheck.py  health_monitor.py  health_monitor_wrapper.py
    server/
      __init__.py
      __main__.py                 # was vpn-sentinel-server/vpn-sentinel-server.py, wrapped in main()
      Dockerfile                  # was vpn-sentinel-server/Dockerfile
      README.md                   # was vpn-sentinel-server/README.md (if present)
    client/
      __init__.py
      __main__.py                 # was vpn-sentinel-client/vpn-sentinel-client.py, wrapped in main()
      Dockerfile
      README.md
pyproject.toml
```

The `vpn-sentinel-server/` and `vpn-sentinel-client/` directories are deleted.

## Migration mechanics

### Import rewrite (the bulk — 429 occurrences / 84 files)
- Repo-wide: `vpn_sentinel_common` → `vpn_sentinel.common` (bulk `sed`, then verify with the suite).
  This covers tests, entry points, Dockerfiles, pyproject, docs, `.claude/`, CodeQL.
- Inside `src/vpn_sentinel/common/`, convert the 22 absolute self-imports
  (`from vpn_sentinel_common.x import …` / `import vpn_sentinel_common.x`) to **relative**
  (`from .x import …`). The 2 existing relative imports stay.
- Entry points (`__main__.py`): import `from vpn_sentinel.common.x import …`; **remove the
  `sys.path.insert(...)` lines** (no longer needed — the package is installed via `pip install -e .`).

### Entry points → `main()` + `__main__.py`
- Move each hyphenated entry script to `src/vpn_sentinel/{server,client}/__main__.py`.
- Wrap the module's top-level execution code in `def main(): ...` and end with
  `if __name__ == "__main__": main()`. Module-level imports/constants stay at module level. This is
  the only logic-shaped change and must preserve behavior (the same code runs, now under `main()`).

### Packaging (`pyproject.toml`)
- `[project] name = "vpn-sentinel"` (was `vpn-sentinel-common`).
- `[tool.setuptools.packages.find] where = ["src"]`, `include = ["vpn_sentinel*"]`.
- Add:
  ```toml
  [project.scripts]
  vpn-sentinel-server = "vpn_sentinel.server.__main__:main"
  vpn-sentinel-client = "vpn_sentinel.client.__main__:main"
  ```
- The pytest config block (`[tool.pytest.ini_options]`) stays; no coverage flags in global addopts
  (kept from Spec 2).

### Dockerfiles (`src/vpn_sentinel/{server,client}/Dockerfile`)
- Build context stays the repo root.
- `COPY pyproject.toml .` + `COPY src/ ./src/`; `pip install -e .` (or `--user` as today).
- `CMD ["python", "-m", "vpn_sentinel.server"]` (resp. `client`).
- Update health_scripts COPY paths to `src/vpn_sentinel/common/health_scripts/...`.
- Preserve the existing multi-stage build, non-root user, and HEALTHCHECK behavior.

### CI (`.github/workflows/ci-cd.yml`)
- Build/scan/publish matrices: set explicit `dockerfile: src/vpn_sentinel/server/Dockerfile` (resp.
  client). **Image tags and `dockerhub_repo` stay `vpn-sentinel-server` / `vpn-sentinel-client`** —
  decouple the (now `src/`) Dockerfile path from the image name in the matrix entries.
- flake8 step: `vpn-sentinel-server/ vpn_sentinel_common/` → `src/`.
- Unit job coverage: `--cov=vpn_sentinel_common` → `--cov=vpn_sentinel`.
- The `vpn-sentinel-server-test` compose service name (in `tests/docker-compose.test.yaml`) is a
  container/service name, not a path — it stays.

### Compose & deployments
- `tests/docker-compose.test.yaml`: `dockerfile: src/vpn_sentinel/{server,client}/Dockerfile`.
- `deployments/server-central/compose.yaml`, `deployments/client-standalone/compose.yaml`:
  `dockerfile:` paths updated. Image-based deployments (`all-in-one`, `client-with-vpn`) reference
  `agigante80/vpn-sentinel-*:latest` — unchanged.
- Root `compose.yaml` references images `vpn-sentinel-{server,client}:latest` (built tags) — unchanged.

### Tests
- All `vpn_sentinel_common` imports → `vpn_sentinel.common` (covered by the bulk rewrite).
- Subprocess invocation: `tests/helpers.py` and the integration tests pass a client-script path
  (`../../vpn-sentinel-client/vpn-sentinel-client.py`). Repoint to
  `src/vpn_sentinel/client/__main__.py`. `tests/helpers.py:start_client_with_monitor` keeps running
  it as `python3 <path>` — valid because the package is installed and entry imports are absolute.
- `tests/run_tests.sh` py_compile paths → the new `__main__.py` paths.
- `tests/README.md` path examples updated.

### Docs & config
- `README.md`, `docs/*`, `CLAUDE.md`, `.claude/commands/{build,lint}.md`,
  `.claude/skills/vpnsentinel/SKILL.md`, `dockerhub/*`, `.github/codeql/codeql-config.yml`:
  update path mentions (`vpn-sentinel-server/Dockerfile` → `src/vpn_sentinel/server/Dockerfile`;
  `python ./vpn-sentinel-server.py` → `python -m vpn_sentinel.server`; `vpn_sentinel_common` →
  `vpn_sentinel.common`).

### Bonus cleanup
- `git rm` the tracked `tests/coverage.xml`; add `tests/coverage.xml` and `tests/coverage_html/` to
  `.gitignore` (same artifact class Spec 2 cleaned).

## Verification strategy (per task)

- After the import rewrite / common move: `python -m pytest tests/unit/` → 559 passed / 93 skipped,
  exit 0; `python -c "import vpn_sentinel.common.config"` succeeds.
- After entry points: `python -m vpn_sentinel.server --help` and `... client --help` run; `pip install
  -e .` then the `vpn-sentinel-server`/`-client` console scripts resolve.
- After Dockerfiles + build refs: **`bin/local-env verify`** → green 23/23 (this rebuilds both images
  from `src/...` Dockerfiles and runs the live E2E — the decisive gate).
- CI edits: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci-cd.yml'))"`.
- flake8 over `src/` clean (max line length 120).
- Final: repo-wide grep for `vpn_sentinel_common`, `vpn-sentinel-server/`, `vpn-sentinel-client/`,
  `vpn-sentinel-server.py`, `vpn-sentinel-client.py` returns nothing (outside `.git`, `.superpowers`,
  `docs/superpowers`).

## Risks

- **Scale (84 files):** a missed reference breaks a build or import. Mitigation: bulk `sed` for the
  uniform rewrite, then the grep gate + the full suite + `bin/local-env verify`.
- **Editable install with `src/` layout:** `pip install -e .` must expose `vpn_sentinel` from `src/`.
  Mitigation: verify `import vpn_sentinel.common` from a clean `pip install -e .` before relying on it
  in Docker.
- **Entry `main()` wrapping:** must not change runtime behavior (e.g., code that ran at import time
  vs inside `main()`). Mitigation: move only the top-level *execution* block into `main()`; keep
  imports/constants/module setup at module scope; `bin/local-env verify` exercises the real client +
  server end-to-end.
- **CI matrix decoupling:** the matrix currently derives both the Dockerfile path and the image tag
  from one `component` value. Splitting them risks a mismatched tag. Mitigation: explicit per-entry
  `dockerfile` + explicit `vpn-sentinel-<x>` tag; validate YAML and diff the matrix carefully.

## Acceptance criteria

- `src/vpn_sentinel/{common,server,client}/` exists; `vpn-sentinel-server/`, `vpn-sentinel-client/`,
  and top-level `vpn_sentinel_common/` are gone.
- `import vpn_sentinel.common.<mod>` works; `python -m vpn_sentinel.server` / `... client` run; the
  `vpn-sentinel-server` / `vpn-sentinel-client` console scripts resolve after `pip install -e .`.
- No `sys.path.insert` hacks remain in the entry points.
- `bin/local-env verify` green 23/23 (images rebuilt from `src/...` Dockerfiles); unit 559/93 exit 0;
  flake8 clean; CI YAML valid.
- Docker Hub image names unchanged (`agigante80/vpn-sentinel-server` / `-client`).
- `tests/coverage.xml` removed and gitignored.
- Repo-wide grep for every old path/name returns nothing.

## Follow-on
- **Spec 3:** internal code refactor of `vpn_sentinel.common` modules and the entry points.
