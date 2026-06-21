# Design: Spec 2 — Repository Restructure (Declutter + Consolidate)

- **Date:** 2026-06-21
- **Status:** Approved (design); pending implementation plan
- **Author:** Claude (with agigante80)
- **Scope:** Spec 2 of 3. Root declutter, Compose consolidation, and `tests/` reorganization.
  The source/package rename (`vpn-sentinel-*` → consistent layout) is **deferred to Spec 2b**.
  Code refactor is **Spec 3**. Every move in this spec is guarded by `bin/local-env verify`,
  the unit suite, and CI-YAML validation — the safety net built in Spec 1 (#76).

## Problem

The repository layout is cluttered and inconsistent:
- Root holds loose shell scripts (`demo_versioning.sh`, `get_version.sh`, `test_client_call.sh`),
  a committed CI artifact (`unit-test-results.xml`), and two near-duplicate dev Compose files
  (`compose.yaml` with VPN vs `compose-no-vpn.yaml`, differing by ~53 lines).
- A junk path `tests/{}` (a shell-expansion bug) is tracked.
- `tests/` has loose top-level scripts and a `tests/integration_server/` dir whose 4 files share
  basenames with `tests/integration/` (`test_e2e.py`, `test_health_integration.py`,
  `test_client_multi_process.py`, `test_dedicated_health_port.py`), making "which test_e2e?"
  ambiguous even though the split is intentional (server-dependent, gated by
  `VPN_SENTINEL_SERVER_TESTS=1`).

## Goals

- A clean, conventional root.
- One dev Compose file using a `vpn` profile instead of two near-duplicates.
- A `tests/` tree where every directory's purpose is unambiguous.
- Zero behavior change: the test suites, CI, image builds, and `bin/local-env verify` all stay
  green throughout.

## Non-Goals (deferred)

- **Spec 2b:** renaming `vpn-sentinel-server/`, `vpn-sentinel-client/` and their hyphenated `.py`
  entry points to a consistent importable layout (~35-file blast radius — Dockerfiles, CI, CodeQL,
  compose, dockerhub, docs, tests). Out of scope here.
- **Spec 3:** code refactor of `vpn_sentinel_common/` and the entry points.
- `deployments/*/compose.yaml` — left as self-contained copy-paste examples (their purpose).
- `tests/docker-compose.test.yaml` — unchanged (it is the `/local-env` stack; renaming it is
  blast-radius without benefit here).

## Decisions (locked during brainstorming)

1. Scope: declutter + Compose consolidation + `tests/` reorg now; source rename is Spec 2b.
2. Compose: merge `compose.yaml` + `compose-no-vpn.yaml` into one `compose.yaml` with a `vpn`
   profile; keep `deployments/*` as-is.
3. `get_version.sh`: **move** to `scripts/` and update all 6 references.
4. `pytest.ini`: **fold** into `pyproject.toml` `[tool.pytest.ini_options]`.

## Changes

### A. Root declutter

**Delete:**
- `tests/{}` — tracked junk (shell-expansion artifact).
- `unit-test-results.xml` — committed CI artifact; remove and add `unit-test-results.xml` (and
  `test-results.xml`) to `.gitignore`.

**Move into `scripts/`:**
- `demo_versioning.sh` → `scripts/demo_versioning.sh`
- `test_client_call.sh` → `scripts/test_client_call.sh`
- `get_version.sh` → `scripts/get_version.sh` — **highest-care move.** Update all 6 references:
  `.github/workflows/ci-cd.yml`, `docs/VERSIONING.md`, `docs/ARCHITECTURE.md`,
  `tests/unit/test_versioning.py`, `.claude/settings.json`
  (`Bash(./get_version.sh)` → `Bash(./scripts/get_version.sh)`), and the self-reference in
  `demo_versioning.sh` (itself moving to `scripts/`). The implementation must re-grep for
  `get_version` to catch any ref this list missed. The unit test `test_versioning.py` and
  CI-YAML validation gate this move.

**Fold config:**
- Move `pytest.ini` `[tool:pytest]` settings into `pyproject.toml` `[tool.pytest.ini_options]`
  (same keys: `testpaths`, `addopts` incl. `--cov-fail-under=80`, `markers`, `filterwarnings`);
  delete `pytest.ini`. Confirm with a full `pytest tests/unit/` run (coverage gate still enforced).

**Stays at root:** `README.md`, `LICENSE`, `CLAUDE.md`, `pyproject.toml`, `.env.example`,
`VERSION`, `.gitignore`, `.pre-commit-config.yaml`, `.shellcheckrc`, `compose.yaml`, `bin/`.

### B. Compose consolidation

- Merge `compose.yaml` (VPN) and `compose-no-vpn.yaml` into a single `compose.yaml`: the VPN
  service (and any service that depends on it via `network_mode: service:vpn-*`) gets
  `profiles: ["vpn"]`. Result:
  - `docker compose up` → no-VPN stack (the former `compose-no-vpn.yaml` behavior)
  - `docker compose --profile vpn up` → full stack with the VPN container
- Delete `compose-no-vpn.yaml`.
- Update the 3 functional references:
  - `tests/run_tests.sh` (its compose-file validation list — drop `compose-no-vpn.yaml`)
  - `tests/integration/test_e2e.py` (`test_docker_compose_syntax` — point at the merged file/profiles)
  - `vpn-sentinel-client/Dockerfile` (any comment/label referencing `compose-no-vpn.yaml`)
- Update doc/CLAUDE mentions of the two-file setup to the profile form.
- `deployments/*` and `tests/docker-compose.test.yaml` untouched.

### C. tests/ reorganization

- Delete `tests/{}` (above).
- Create `tests/manual/` and move the 3 loose, manually-run scripts there:
  `test_telegram_manual.py`, `healthcheck_probe.py`, `test_health_server_simple.py`. (These are
  `#!/usr/bin/env python3` scripts, not part of the auto-collected `unit/`/`integration/` suites.)
  Ensure they are not collected by default (they live outside `testpaths` subdirs that CI runs, or
  are marked); confirm `pytest tests/unit/` and `bin/local-env verify` are unaffected.
- Rename `tests/integration_server/` → `tests/integration/server_dependent/` so the
  server-dependent suite nests visibly under integration and the basename collision with
  `tests/integration/` is resolved structurally. Update:
  - `tests/integration_server/README.md` content/paths (moves with the dir)
  - any `VPN_SENTINEL_SERVER_TESTS` run instructions (self-contained to that dir + README)
  - `tests/run_tests.sh` if it references the path
  - Note: `tests/integration_server/test_health_server_simple.py` duplicates the root
    `tests/test_health_server_simple.py` being moved to `tests/manual/`. Keep the
    server_dependent copy (it belongs to that gated suite); the root copy moves to `tests/manual/`.
    If the two are byte-identical, the root one is the redundant duplicate — still move it to
    `tests/manual/` (do not silently delete; the plan's characterization step confirms identity).
- `unit/`, `smoke/`, `fixtures/`, `utils/`, `helpers.py`, `conftest.py`, `requirements.txt`,
  `.env.test`, `docker-compose.test.yaml`, `run_tests.sh`, `README.md` stay where they are.

### D. Verification strategy (per move)

Each implementation task ends by running the gate appropriate to what it touched:
- Moved tests / folded pytest config → `python -m pytest tests/unit/` (coverage gate intact).
- Anything touching compose / the stack → `bin/local-env verify` (must stay 23/23 green).
- CI workflow edits → `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci-cd.yml'))"`.
- `get_version.sh` move → run `./scripts/get_version.sh` and confirm output; run
  `pytest tests/unit/test_versioning.py`.
- Shell scripts → `shellcheck` + `shfmt -i 2 -ci`.
- Final: a repo-wide grep proving no dangling references to moved/deleted paths.

## Risks

- **`get_version.sh` move** touches the CI versioning path, which `bin/local-env verify` does not
  cover. Mitigation: update all 6 refs in one task, run `test_versioning.py` + the script from its
  new path + CI-YAML validation; the actual CI versioning job only runs on push (watch the first
  develop push after merge).
- **Compose profile merge** could change default `up` behavior. Mitigation: the merged default
  (`up` with no profile) must reproduce the former `compose-no-vpn.yaml` topology; verify by
  `docker compose config` and a no-profile `up` smoke.
- **tests/ moves** can change pytest collection. Mitigation: run the unit suite after each move and
  confirm the count is unchanged (562 passed / 93 skipped baseline).

## Acceptance criteria

- Root no longer contains `demo_versioning.sh`, `get_version.sh`, `test_client_call.sh`,
  `pytest.ini`, `compose-no-vpn.yaml`, or `unit-test-results.xml`.
- `scripts/` contains the three moved scripts; all 6 `get_version.sh` references updated; no
  dangling refs (grep clean).
- One `compose.yaml` with a working `vpn` profile; `docker compose config` valid for both
  default and `--profile vpn`; `compose-no-vpn.yaml` gone with no dangling refs.
- `pytest.ini` gone; `pyproject.toml` carries the pytest config; `pytest tests/unit/` passes with
  the 80% coverage gate enforced (562 passed / 93 skipped, unchanged).
- `tests/{}` gone; `tests/manual/` holds the 3 moved scripts; `tests/integration_server/` renamed
  to `tests/integration/server_dependent/` with refs updated.
- `bin/local-env verify` green (23/23) at the end; unit suite unchanged; CI YAML valid.
- No reference anywhere (code/docs/CI) to a moved/deleted path.

## Follow-on (context, not scope)

- **Spec 2b:** source/package rename to a consistent importable layout, verify-guarded.
- **Spec 3:** code refactor of `vpn_sentinel_common/` and entry points.
