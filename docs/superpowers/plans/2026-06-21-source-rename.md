# Spec 2b Source/Package Rename — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collapse `vpn-sentinel-server/`, `vpn-sentinel-client/`, and `vpn_sentinel_common/` into one importable `src/vpn_sentinel/{common,server,client}` namespace, with image names and behavior unchanged.

**Architecture:** A mechanical move + import rewrite. `git mv` for relocations, a scoped bulk `sed` for `vpn_sentinel_common`→`vpn_sentinel.common`, and explicit edits for Dockerfiles/CI/compose. The entry scripts ALREADY have `def main()` + `if __name__ == "__main__": main()`, so `python -m vpn_sentinel.server` and console_scripts work with no logic change. `bin/local-env verify` rebuilds both images from the new `src/` Dockerfiles and runs the E2E — the decisive gate.

**Tech Stack:** git, Python 3.12 / setuptools (src layout) / pytest, Docker (multi-stage), bash.

## Global Constraints

- Branch: `develop`. Commit after each task. End each commit message with:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- ZERO behavior change for users. **Docker Hub image names stay `agigante80/vpn-sentinel-server` and
  `agigante80/vpn-sentinel-client`** (CI tags), independent of the new `src/` Dockerfile paths.
- Baselines: unit suite `python -m pytest tests/unit/` → **559 passed / 93 skipped**, exit 0 (no
  coverage gate — Spec 2). `bin/local-env verify` → **23/23** green, exit 0, no leftover containers.
- The bulk rewrite is scoped to text sources and MUST exclude `.git/`, `.superpowers/`,
  `docs/superpowers/`, and Dockerfiles (Dockerfiles are edited by hand in Task 3).
- After each move, a repo-wide grep for the old path/name (excluding `.git`, `.superpowers`,
  `docs/superpowers`) must return nothing relevant.
- Do NOT touch test skips or `tests/integration/` collection structure (the dormant
  `server_dependent/` basename collision stays dormant — out of scope).
- flake8 max line length 120; shell passes shellcheck/shfmt.

---

### Task 1: Move common package to src/ and rewrite all imports

**Files:**
- Move: `vpn_sentinel_common/` → `src/vpn_sentinel/common/`
- Create: `src/vpn_sentinel/__init__.py`
- Modify: `pyproject.toml` (name, packages.find, scripts)
- Bulk-modify: every text source referencing `vpn_sentinel_common` (tests, docs, `.claude/`, CI, etc.) EXCEPT Dockerfiles

**Interfaces:**
- Produces: importable `vpn_sentinel.common.<module>`; distribution `vpn-sentinel`; console_script
  declarations consumed by Task 2's entry points.

- [ ] **Step 1: Create the namespace and move common**

```bash
mkdir -p src/vpn_sentinel
git mv vpn_sentinel_common src/vpn_sentinel/common
printf '"""VPN Sentinel — unified namespace package."""\n' > src/vpn_sentinel/__init__.py
git add src/vpn_sentinel/__init__.py
```
Expected: `src/vpn_sentinel/common/` holds the 21 modules + `health_scripts/`; `vpn_sentinel_common/` is gone.

- [ ] **Step 2: Bulk-rewrite `vpn_sentinel_common` → `vpn_sentinel.common` (excluding Dockerfiles)**

```bash
grep -rl 'vpn_sentinel_common' . \
  --include='*.py' --include='*.toml' --include='*.yml' --include='*.yaml' \
  --include='*.md' --include='*.sh' --include='*.cfg' --include='*.ini' \
  | grep -v '\.git/\|\.superpowers/\|docs/superpowers/' \
  | xargs sed -i 's/vpn_sentinel_common/vpn_sentinel.common/g'
```
Expected: no `vpn_sentinel_common` left in those files. (Dockerfiles still say `vpn_sentinel_common`; Task 3 fixes them.)

- [ ] **Step 3: Convert the flat common modules' self-imports to relative**

The flat modules in `src/vpn_sentinel/common/*.py` now import siblings as
`from vpn_sentinel.common.X import …` / `import vpn_sentinel.common.X`. Convert those to relative:

```bash
# from vpn_sentinel.common.X import ...  ->  from .X import ...
sed -i -E 's/from vpn_sentinel\.common\.([a-zA-Z_][a-zA-Z0-9_]*) import/from .\1 import/g' src/vpn_sentinel/common/*.py
# import vpn_sentinel.common.X            ->  from . import X
sed -i -E 's/^import vpn_sentinel\.common\.([a-zA-Z_][a-zA-Z0-9_]*)$/from . import \1/g' src/vpn_sentinel/common/*.py
```
Leave `src/vpn_sentinel/common/health_scripts/*.py` using absolute `vpn_sentinel.common.X` imports
(subdir depth makes relative noisier; absolute works). Then check nothing absolute-self-imports
remains in the flat modules: `grep -n 'vpn_sentinel.common' src/vpn_sentinel/common/*.py` should show
only non-import usages (e.g. strings/log labels), if any.

- [ ] **Step 4: Update pyproject.toml packaging**

In `pyproject.toml`, set:
```toml
[project]
name = "vpn-sentinel"
```
(change the `name` line only; keep version/description/readme/requires-python/authors/license/dependencies)

Replace the packages-find block:
```toml
[tool.setuptools.packages.find]
where = ["src"]
include = ["vpn_sentinel*"]
```

Add a scripts table (place after `[project]` block or near the find block):
```toml
[project.scripts]
vpn-sentinel-server = "vpn_sentinel.server.__main__:main"
vpn-sentinel-client = "vpn_sentinel.client.__main__:main"
```
(The `vpn_sentinel.server`/`client` packages are created in Task 2; declaring the scripts now is fine
— they resolve after Task 2 + reinstall.)

- [ ] **Step 5: Reinstall and verify imports + unit suite**

```bash
python3 -m pip install -e . --quiet 2>&1 | tail -2 || python3 -m pip install -e . --user --quiet
python3 -c "import vpn_sentinel.common.config as c; print('import ok:', c.__name__)"
python -m pytest tests/unit/ -q 2>&1 | tail -3
```
Expected: `import ok: vpn_sentinel.common.config`; unit suite `559 passed, 93 skipped`, exit 0.
(If install needs a venv per PEP 668, use the active venv; do NOT use `--break-system-packages`.)

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor(pkg): move vpn_sentinel_common to src/vpn_sentinel/common; rewrite imports

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Move entry scripts to src/vpn_sentinel/{server,client}

**Files:**
- Create: `src/vpn_sentinel/server/__init__.py`, `src/vpn_sentinel/client/__init__.py`
- Move: `vpn-sentinel-server/vpn-sentinel-server.py` → `src/vpn_sentinel/server/__main__.py`
- Move: `vpn-sentinel-client/vpn-sentinel-client.py` → `src/vpn_sentinel/client/__main__.py`
- Move: `vpn-sentinel-client/README.md` → `src/vpn_sentinel/client/README.md`
- Modify: the two `__main__.py` (remove `sys.path` hacks)

**Interfaces:**
- Consumes: `vpn_sentinel.common.*` (Task 1), the console_script declarations (Task 1).
- Produces: `python -m vpn_sentinel.server` / `... client`; `main()` callables for console_scripts.

- [ ] **Step 1: Create the server/client packages and move the entry files**

```bash
mkdir -p src/vpn_sentinel/server src/vpn_sentinel/client
printf '"""VPN Sentinel server entry package."""\n' > src/vpn_sentinel/server/__init__.py
printf '"""VPN Sentinel client entry package."""\n' > src/vpn_sentinel/client/__init__.py
git add src/vpn_sentinel/server/__init__.py src/vpn_sentinel/client/__init__.py
git mv vpn-sentinel-server/vpn-sentinel-server.py src/vpn_sentinel/server/__main__.py
git mv vpn-sentinel-client/vpn-sentinel-client.py src/vpn_sentinel/client/__main__.py
git mv vpn-sentinel-client/README.md src/vpn_sentinel/client/README.md
```
(After these, `vpn-sentinel-server/` retains only its `Dockerfile` and `vpn-sentinel-client/` only its
`Dockerfile` — moved in Task 3. The entry `.py` files already had their `vpn_sentinel_common` imports
rewritten to `vpn_sentinel.common` by Task 1's bulk sed.)

- [ ] **Step 2: Remove the sys.path hacks from both __main__.py**

In `src/vpn_sentinel/server/__main__.py`, delete the line:
```python
sys.path.insert(0, '/app')
```
In `src/vpn_sentinel/client/__main__.py`, delete the lines:
```python
# Add the parent directory to sys.path so we can import vpn_sentinel_common
sys.path.insert(0, str(Path(__file__).parent.parent))
```
If removing the client line makes `Path`/`sys` imports unused, leave the imports (they may be used
elsewhere in the file) — verify with flake8 in Step 4 and only remove a now-unused import if flake8
(F401) flags it.

- [ ] **Step 3: Reinstall and verify the entry points import and console scripts resolve**

```bash
python3 -m pip install -e . --quiet 2>&1 | tail -1 || true
python3 -c "from vpn_sentinel.server.__main__ import main as m; print('server main:', m.__name__)"
python3 -c "from vpn_sentinel.client.__main__ import main as m; print('client main:', m.__name__)"
python3 -c "import importlib.util as u; print('server runnable:', u.find_spec('vpn_sentinel.server.__main__') is not None)"
command -v vpn-sentinel-server && command -v vpn-sentinel-client
```
Expected: both `main` functions import; both console scripts resolve to paths.

- [ ] **Step 4: flake8 the moved entry files + unit suite still green**

```bash
flake8 --max-line-length=120 src/vpn_sentinel/server/__main__.py src/vpn_sentinel/client/__main__.py
python -m pytest tests/unit/ -q 2>&1 | tail -2
```
Expected: flake8 clean; `559 passed, 93 skipped`.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(pkg): move entry scripts to src/vpn_sentinel/{server,client}; drop sys.path hacks

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Move Dockerfiles into src/ and update all build references

**Files:**
- Move: `vpn-sentinel-server/Dockerfile` → `src/vpn_sentinel/server/Dockerfile`
- Move: `vpn-sentinel-client/Dockerfile` → `src/vpn_sentinel/client/Dockerfile`
- Modify: both Dockerfiles (COPY paths, CMD)
- Modify: `tests/docker-compose.test.yaml`, `.github/workflows/ci-cd.yml` (matrix dockerfile paths),
  `deployments/server-central/compose.yaml`, `deployments/client-standalone/compose.yaml`

**Interfaces:**
- Consumes: the `src/vpn_sentinel/...` layout (Tasks 1–2).
- Produces: images that build from `src/` Dockerfiles, tagged with the unchanged image names.

- [ ] **Step 1: Move the Dockerfiles (this also removes the now-empty hyphen dirs)**

```bash
git mv vpn-sentinel-server/Dockerfile src/vpn_sentinel/server/Dockerfile
git mv vpn-sentinel-client/Dockerfile src/vpn_sentinel/client/Dockerfile
```
Expected: `vpn-sentinel-server/` and `vpn-sentinel-client/` no longer exist.

- [ ] **Step 2: Update the SERVER Dockerfile (`src/vpn_sentinel/server/Dockerfile`)**

Make these edits (the file is multi-stage; apply in both builder and runtime stages as present):
- Builder: `COPY vpn_sentinel_common/ ./vpn_sentinel_common/` → `COPY src/ ./src/`
- Runtime: `COPY vpn_sentinel_common/ ./vpn_sentinel_common/` → `COPY src/ ./src/`
- Delete the lines `COPY vpn-sentinel-server/vpn-sentinel-server.py ./vpn-sentinel-server.py` and
  `RUN chmod +x ./vpn-sentinel-server.py` (the entry now ships inside the installed package).
- `CMD ["python", "./vpn-sentinel-server.py"]` → `CMD ["python", "-m", "vpn_sentinel.server"]`
- Keep `COPY pyproject.toml .` and the `pip install -e .` line. Because the install is editable, the
  source must exist at the same path at runtime — `COPY src/ ./src/` in the runtime stage provides it
  and `WORKDIR /app` keeps the path stable. (If `bin/local-env verify` later shows a
  ModuleNotFoundError for `vpn_sentinel`, switch the builder install from `-e .` to `.` so the package
  is baked into `/root/.local`, and drop the runtime `COPY src/`.)

- [ ] **Step 3: Update the CLIENT Dockerfile (`src/vpn_sentinel/client/Dockerfile`)**

- `COPY vpn-sentinel-client/ /app/` → `COPY src/vpn_sentinel/client/ /app/client_pkg/` is NOT needed;
  instead remove that whole-dir copy and rely on the editable install. Concretely:
  - `COPY vpn_sentinel_common/ /app/vpn_sentinel_common/` → `COPY src/ /app/src/`
  - `COPY pyproject.toml /app/pyproject.toml` stays.
  - `COPY vpn_sentinel_common/health_scripts/healthcheck.py /app/healthcheck.py` →
    `COPY src/vpn_sentinel/common/health_scripts/healthcheck.py /app/healthcheck.py`
  - `COPY vpn_sentinel_common/health_scripts/health_monitor_wrapper.py /app/health-monitor.py` →
    `COPY src/vpn_sentinel/common/health_scripts/health_monitor_wrapper.py /app/health-monitor.py`
  - `COPY vpn-sentinel-client/vpn-sentinel-client.py /app/vpn-sentinel-client.py` → delete (the entry
    ships in the installed package).
  - The `chmod +x`/verify `RUN` block that lists `/app/vpn-sentinel-client.py` → drop that path from
    the list (keep `/app/health-monitor.py` and `/app/healthcheck.py`).
  - `CMD ["/app/vpn-sentinel-client.py"]` → `CMD ["python", "-m", "vpn_sentinel.client"]`
  - Keep `pip install -e /app` (or `-e .`); same editable-source caveat as the server.

- [ ] **Step 4: Update the build references**

`tests/docker-compose.test.yaml`:
- `dockerfile: vpn-sentinel-server/Dockerfile` → `dockerfile: src/vpn_sentinel/server/Dockerfile`
- `dockerfile: vpn-sentinel-client/Dockerfile` → `dockerfile: src/vpn_sentinel/client/Dockerfile`

`.github/workflows/ci-cd.yml` (build, scan, publish matrices — all occurrences):
- `dockerfile: vpn-sentinel-server/Dockerfile` → `dockerfile: src/vpn_sentinel/server/Dockerfile`
- `dockerfile: vpn-sentinel-client/Dockerfile` → `dockerfile: src/vpn_sentinel/client/Dockerfile`
- Where the matrix uses `file: vpn-sentinel-${{ matrix.component }}/Dockerfile`, change to
  `file: src/vpn_sentinel/${{ matrix.component }}/Dockerfile`. **Leave image tags / `dockerhub_repo`
  values (`vpn-sentinel-server`, `vpn-sentinel-client`, `agigante80/vpn-sentinel-*`) unchanged.**

`deployments/server-central/compose.yaml`, `deployments/client-standalone/compose.yaml`:
- `dockerfile: vpn-sentinel-server/Dockerfile` → `dockerfile: src/vpn_sentinel/server/Dockerfile`
  (resp. client). The `context: ../..` stays.

- [ ] **Step 5: Validate YAML and run the decisive gate**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci-cd.yml')); print('ci yaml ok')"
python3 -c "import yaml; yaml.safe_load(open('tests/docker-compose.test.yaml')); print('test compose ok')"
docker compose -f tests/docker-compose.test.yaml --env-file tests/.env.test config >/dev/null && echo "compose config ok"
bin/local-env verify
```
Expected: YAML ok; `bin/local-env verify` rebuilds BOTH images from `src/...` Dockerfiles and the live
E2E passes — **23/23 green, exit 0, no containers left**. If a build fails on `vpn_sentinel` import,
apply the non-editable-install fallback from Step 2/3 and re-run `bin/local-env verify`.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "build(docker): move Dockerfiles into src/; build images from src/ layout (image names unchanged)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Update remaining references (tests, CI lint/cov, CodeQL, docs, .claude)

**Files:**
- Modify: `tests/helpers.py`, the integration tests that reference the client script path,
  `tests/run_tests.sh`, `tests/README.md`, `.github/workflows/ci-cd.yml` (flake8 + coverage),
  `.github/codeql/codeql-config.yml`, `README.md`, `docs/*`, `CLAUDE.md`,
  `.claude/commands/build.md`, `.claude/commands/lint.md`, `.claude/skills/vpnsentinel/SKILL.md`,
  `dockerhub/*`

**Interfaces:**
- Consumes: the new `src/` layout and `python -m` entry points.

- [ ] **Step 1: Find every remaining old-path reference**

```bash
grep -rn 'vpn-sentinel-server/\|vpn-sentinel-client/\|vpn-sentinel-server\.py\|vpn-sentinel-client\.py' . \
  | grep -v '\.git/\|\.superpowers/\|docs/superpowers/'
```
Record each hit; every one is updated in Steps 2–4.

- [ ] **Step 2: Repoint the test subprocess invocation**

In the integration tests and `tests/helpers.py`, the client script path
`../../vpn-sentinel-client/vpn-sentinel-client.py` → `../../src/vpn_sentinel/client/__main__.py`. Apply
across the test files that set `self.client_script = os.path.join(os.path.dirname(__file__), '...')`:
```bash
grep -rl 'vpn-sentinel-client/vpn-sentinel-client.py' tests/ \
  | xargs sed -i 's#vpn-sentinel-client/vpn-sentinel-client.py#src/vpn_sentinel/client/__main__.py#g'
grep -rl 'vpn-sentinel-server/vpn-sentinel-server.py' tests/ \
  | xargs sed -i 's#vpn-sentinel-server/vpn-sentinel-server.py#src/vpn_sentinel/server/__main__.py#g'
```
`tests/helpers.py:start_client_with_monitor` keeps invoking `python3 <path>` — valid because the
package is installed and the entry uses absolute `vpn_sentinel.common` imports.

- [ ] **Step 3: Update CI lint/coverage and run_tests/README**

`.github/workflows/ci-cd.yml`:
- flake8 step: `flake8 vpn-sentinel-server/ vpn_sentinel.common/ ...` → `flake8 src/ ...`
  (the Task 1 sed already turned `vpn_sentinel_common/` into `vpn_sentinel.common/` here; replace the
  whole path list with `src/`).
- unit coverage: ensure the unit job uses `--cov=vpn_sentinel` (Task 1's sed produced
  `--cov=vpn_sentinel.common`; broaden to `--cov=vpn_sentinel` to cover server/client too).

`tests/run_tests.sh`: the py_compile paths `vpn-sentinel-server/vpn-sentinel-server.py` /
`vpn-sentinel-client/vpn-sentinel-client.py` → `src/vpn_sentinel/server/__main__.py` /
`src/vpn_sentinel/client/__main__.py`.

`tests/README.md`: same path examples.

- [ ] **Step 4: Update docs, CLAUDE.md, .claude/, CodeQL, dockerhub**

Update every remaining hit from Step 1 to the new paths/commands:
- `vpn-sentinel-server/Dockerfile` → `src/vpn_sentinel/server/Dockerfile` (resp. client)
- `python ./vpn-sentinel-server.py` / `./vpn-sentinel-client.py` → `python -m vpn_sentinel.server` /
  `python -m vpn_sentinel.client`
- `vpn-sentinel-server/vpn-sentinel-server.py` (e.g. in `.claude/commands/build.md`,
  `.claude/commands/lint.md`, `CLAUDE.md`, `docs/*`, `dockerhub/*`,
  `.github/codeql/codeql-config.yml` comment, `.claude/skills/vpnsentinel/SKILL.md`) → the new
  `src/vpn_sentinel/...` paths.
- In `.claude/commands/build.md`, the `docker build -t vpn-sentinel-server:latest -f
  vpn-sentinel-server/Dockerfile .` → `-f src/vpn_sentinel/server/Dockerfile .` (resp. client), and in
  `CLAUDE.md`'s commands block likewise.

- [ ] **Step 5: Verify everything green and no dangling references**

```bash
flake8 --max-line-length=120 src/
python -m pytest tests/unit/ -q 2>&1 | tail -2
python -m pytest tests/integration/ --co -q 2>&1 | tail -3
grep -rn 'vpn-sentinel-server/\|vpn-sentinel-client/\|vpn-sentinel-server\.py\|vpn-sentinel-client\.py\|vpn_sentinel_common' . \
  | grep -v '\.git/\|\.superpowers/\|docs/superpowers/'
```
Expected: flake8 clean; unit `559 passed, 93 skipped`; integration collects with no import errors; the
final grep returns NOTHING (every old path/name gone). Note: `vpn-sentinel-server`/`vpn-sentinel-client`
as IMAGE/service names (no trailing `/` or `.py`) are allowed and intentionally preserved — the grep
patterns above only match the path forms.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor(refs): repoint tests/CI/docs/.claude at src/ layout and python -m entry points

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Cleanup tracked coverage artifacts

**Files:**
- Delete: `tests/coverage.xml`
- Modify: `.gitignore`

- [ ] **Step 1: Confirm tracked artifacts**

```bash
git ls-files tests/coverage.xml tests/coverage_html 2>/dev/null
```
Expected: lists `tests/coverage.xml` (and possibly files under `tests/coverage_html/`).

- [ ] **Step 2: Remove and ignore**

```bash
git rm -r --ignore-unmatch tests/coverage.xml tests/coverage_html
```
Append to `.gitignore`:
```gitignore
# pytest-cov local artifacts
tests/coverage.xml
tests/coverage_html/
```

- [ ] **Step 3: Final verification**

```bash
python -m pytest tests/unit/ -q 2>&1 | tail -2
bin/local-env verify
```
Expected: unit `559 passed, 93 skipped`; `bin/local-env verify` green 23/23, exit 0, no containers left.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove tracked coverage artifacts; gitignore tests/coverage.*

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- `src/vpn_sentinel/{common,server,client}` + namespace `__init__.py` → Tasks 1–2.
- Import rewrite (`vpn_sentinel_common`→`vpn_sentinel.common`) + relative self-imports → Task 1.
- Entry points as `__main__.py`, sys.path hacks removed, `python -m` → Task 2 (already have `main()`).
- pyproject name `vpn-sentinel`, `where=["src"]`, console_scripts → Task 1.
- Dockerfiles in `src/`, `CMD python -m`, image names preserved → Task 3.
- CI matrix dockerfile paths decoupled from image tags, flake8/coverage paths → Tasks 3–4.
- compose + deployments build refs → Task 3.
- tests subprocess paths, run_tests, README, CodeQL, docs, CLAUDE.md, .claude, dockerhub → Task 4.
- `bin/local-env verify` (rebuilds src/ Dockerfiles) as the gate → Tasks 3 & 5.
- `tests/coverage.xml` cleanup → Task 5.

**Placeholder scan:** No TBD/TODO. The Docker editable-install caveat has a concrete fallback (switch
`-e .` → `.`) with `bin/local-env verify` as the proof. The "find every hit" steps re-grep so no
reference list is assumed complete.

**Consistency:** Names match across tasks — `src/vpn_sentinel/common`, `…/server/__main__.py`,
`…/client/__main__.py`, distribution `vpn-sentinel`, console scripts
`vpn_sentinel.server.__main__:main` / `vpn_sentinel.client.__main__:main`, `python -m
vpn_sentinel.server` / `… client`. Baselines (559/93, verify 23/23) stated identically in every gate.

## Out of scope
- **Spec 3:** internal code refactor of `vpn_sentinel.common` modules and the entry points.
- Un-skipping `tests/integration/test_e2e.py` (+ the `__init__.py` the nested `server_dependent/`
  basenames would then require).
