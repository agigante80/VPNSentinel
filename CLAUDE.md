# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

It is the single source of truth for how to work in this repo, for Claude Code and any other agentic
tool. A companion expert skill lives at `.claude/skills/vpnsentinel/SKILL.md`: load it for deep
architecture or operational questions.

## What this project is

VPNSentinel is a **distributed client-server VPN monitoring system**. It watches whether traffic is
actually routing through a VPN, detects DNS leaks, and sends Telegram alerts.

```
[VPN Client container]                 [VPN Server container]
  python -m vpn_sentinel.client          python -m vpn_sentinel.server
  - Keepalive loop (60s)   POST ───────► API :5000  /keepalive
  - Public IP detection                  - Status tracking (in-memory)
  - DNS leak detection                   - Telegram notifications
  - Health subprocess                    - Web dashboard :8080
  network_mode: service:vpn              - Health endpoint :8081
```

**Traffic-light status model:** 🟢 routing correctly · 🟡 DNS leaking · 🔴 VPN bypass (client public
IP == server public IP). Red logic lives in `src/vpn_sentinel/common/api_routes.py`; DNS/yellow logic in
`src/vpn_sentinel/common/network.py`.

**Critical constraint:** the client must run inside the VPN network namespace
(`network_mode: service:vpn-client`) or it cannot detect bypass.

**Critical caveat:** all client state lives in an in-memory dict (`client_status` in
`api_routes.py`). Server restart = all history lost; clients re-register on next keepalive. Flag this
in any PR that adds features depending on historical data or touches restart logic.

## Repository layout

| Path | Purpose |
|---|---|
| `src/vpn_sentinel/server/__main__.py` | Server entry point (starts 3 Flask apps + cleanup thread) |
| `src/vpn_sentinel/client/__main__.py` | Client entry point (keepalive loop, subprocess mgmt) |
| `src/vpn_sentinel/common/` | Shared library (~21 modules), the bulk of the logic |
| `tests/` | `unit/`, `integration/`, `smoke/` + `run_tests.sh` |
| `deployments/` | 4 deployment modes (all-in-one, client-standalone, client-with-vpn, server-central) |
| `docs/` | Architecture, security, testing, Telegram, versioning docs |
| `bin/local-env` | Local Docker E2E stack driver (start/stop/rebuild/status/logs/verify) |
| `scripts/` | Version derivation, release primitive, dead-code scan, dashboard screenshot |
| `.github/workflows/ci-cd.yml` | CI/CD pipeline (version, lint, test, docker build, security scan, publish, integration) |
| `.github/workflows/auto-release.yml` | Auto-release on merge, gated by `scripts/version-lib.sh` |

## Commands (verified against CI and tooling)

```bash
# Tests: full suite (installs deps, runs unit + integration, coverage, cleanup)
./tests/run_tests.sh                 # unit only (unit is the DEFAULT; there is no --unit flag)
./tests/run_tests.sh --integration   # adds integration (needs a running server)
./tests/run_tests.sh --all           # integration + coverage + cleanup

# Tests: direct pytest needs the package importable first (run_tests.sh does this for you)
pip install -e . && pip install -r tests/requirements.txt

# Tests: direct (what CI runs for unit, including the coverage gate)
python -m pytest tests/unit/ --tb=short --cov=vpn_sentinel.common --cov-report=term --cov-fail-under=80

# Tests: one file / one test / one keyword
python -m pytest tests/unit/test_network.py
python -m pytest tests/unit/test_network.py::TestParseDnsTrace          # most tests are class-based
python -m pytest tests/unit/test_network.py::TestParseGeolocation::test_parse_geolocation_invalid_json
python -m pytest tests/unit/ -k "dns_leak"

# Lint: CI runs all three of these and fails on the first two
black --check --line-length 120 src/ tests/     # `black --line-length 120 src/ tests/` to fix
flake8 --max-line-length=120 src/
pylint src/vpn_sentinel/common/                 # advisory only, continue-on-error in CI

# Lint: shell (pre-commit + the /lint command)
shellcheck bin/local-env scripts/*.sh tests/run_tests.sh .githooks/pre-commit
shfmt -i 2 -ci -d bin/local-env scripts/*.sh

# Local E2E stack (tests/docker-compose.test.yaml; API :15554, health :15553, dashboard :18080)
bin/local-env start        # build + up, wait for healthy, print URLs
bin/local-env verify       # up -> live-stack pytest -> teardown (this is the black-box E2E gate)
bin/local-env logs vpn-sentinel-server-test
bin/local-env stop

# Build images (Dockerfiles build from repo root context)
docker build -t vpn-sentinel-server:latest -f src/vpn_sentinel/server/Dockerfile .
docker build -t vpn-sentinel-client:latest -f src/vpn_sentinel/client/Dockerfile .

# Run the production-shaped stack
docker compose up -d
docker compose logs -f vpn-sentinel-server

# Version + dead code
./scripts/get_version.sh              # branch-aware version string
bash scripts/version-lib.sh           # bare run is informational only in git mode (see below)
./scripts/find-dead-code.sh           # vulture scan filtered by .vulture_allowlist.py
```

Coverage gate is **80%** on `vpn_sentinel.common`, enforced in CI's unit job and the `/test` command
(`--cov=vpn_sentinel.common --cov-fail-under=80`). It is NOT in the global pytest addopts, because
black-box E2E/integration runs (`bin/local-env verify`) must stay coverage-free. Python **3.12** in CI
(`requires-python >=3.10`).

## Wiring you cannot see from a single file

- **Three separate Flask apps, not one.** `common/server.py` creates `api_app`, `health_app` and
  `dashboard_app`. `server/__main__.py` runs each in its own daemon thread on its own port.
- **Routes register by import side effect.** `api_routes`, `health_routes` and `dashboard_routes`
  attach their handlers via decorators at import time, so `server/__main__.py` imports them purely
  for that effect (with `# noqa: F401`). A new route module is dead until it is added to that import.
  For the same reason those handler names look unused to static analysis: see `.vulture_allowlist.py`.
- **Shared state is guarded by one lock.** `api_routes.client_status` is a plain dict paired with
  `api_routes.client_status_lock`. Keepalive handlers, the dashboard, and the `cleanup_stale_clients`
  thread all touch it concurrently. Any new read-modify-write must take the lock.
- **The API path prefix is configurable and must match on both sides.** `VPN_SENTINEL_API_PATH`
  (default `/api/v1`) is baked into the route strings in `api_routes.py` at import time and into the
  client URL in `payload.py`. The local test stack deliberately runs on `/test/v1`, which is why
  hardcoding `/api/v1` in a test or a route passes unit tests and then fails `bin/local-env verify`.
- **The client supervises a health subprocess.** `client/__main__.py` runs the keepalive loop in the
  foreground and spawns the health monitor with `subprocess.Popen`, then terminates it on shutdown.
- **`common/health_scripts/` holds backward-compatible CLI shims.** They re-export from
  `healthcheck.py` to keep the old `health_common.py` command line working. This is what the many
  `tests/unit/test_*_shim.py` files pin down. Do not "clean up" a shim without checking those tests.

## Guardrails that will block you

- **A git pre-commit hook rejects the commit** if any staged file contains a home-directory absolute
  path or an RFC 1918 private IP (the class A block, the class C block, or the class B range), or if
  it stages generated artifacts (`tests/coverage_html/`, `htmlcov/`, `tests/coverage.xml`,
  virtualenv dirs). The exact regex is at the top of `.githooks/pre-commit`. It lives in
  `.githooks/pre-commit` and is copied into `.git/hooks/` by `scripts/setup/install-hooks.sh`, so it
  is per-clone and may not be active in a fresh checkout: run that script once. This is the
  enforcement behind the portability rule below. It scans file content, not just paths, so a doc
  example or test fixture using a private IP is blocked too: use a placeholder or a documentation
  range address.
- **A Claude `PreToolUse` hook blocks the unicode em dash (U+2014) and en dash (U+2013)** in any
  Write, Edit, MultiEdit, NotebookEdit or Bash input (`.claude/hooks/block-dashes.py`). The fix is to
  restructure the sentence (colon, comma, parentheses, or two sentences), never to swap in an ASCII
  hyphen. Note that older text already in the repo still contains them; only new writes are checked.
- **`.pre-commit-config.yaml`** runs `shfmt -i 2 -ci`, `black --line-length 120` on `src/` and
  `tests/`, trailing-whitespace and end-of-file fixes.
- **CI fails on `black --check`**, which is easy to miss because the repo has no formatter in the
  test script. Run black before pushing Python changes.

## Versioning and releases

The version is derived, not declared: there is no `VERSION` file. `scripts/get_version.sh` reads
the latest git tag (via `git describe`) and turns it plus branch and commit state into the
published string (`1.1.6` on a clean tag on `main`, `1.1.6-dev-abc1234` on `develop`,
`1.1.6-<branch>-abc1234` elsewhere), and that string becomes the Docker tag.
`scripts/version-lib.sh` is the single shared primitive every release lane consumes; it defaults
to `VERSION_SOURCE=git` (this repo is tag-derived), so `read_version` returns the latest tag
itself and a bare invocation can only ever print `equal` (a tag exists) or `first-release` (it
does not); it is informational, not a release-readiness gate, in that mode. The full four-verdict
table below is what a lane sees when it sets `VERSION_SOURCE` to a file-backed source (`file`,
`node`, `python`, `cargo`) explicitly, comparing a bumped working-tree version against the tag:

| Verdict | Meaning | What to do |
|---|---|---|
| `first-release` | no release tag exists yet | anything may ship |
| `ahead` | working version is past the latest tag | already bumped deliberately: ship as-is, do NOT re-bump |
| `equal` | nobody bumped | the lane decides: block the merge, or auto-patch |
| `behind` | branch is behind a release | regression, hard stop |

Any workflow or script that calls it needs full history and tags (`fetch-depth: 0`,
`fetch-tags: true`), or every check degrades to `first-release`. Details in `docs/VERSIONING.md`.

## Working agreements

- **Branch:** Active development happens on `develop`. `main` is the release branch. Don't commit
  directly to `main`.
- **Commit/push only when asked.** When you do commit, end the message with the Co-Authored-By
  trailer for the model in use.
- **Tests are required** for new functionality: unit tests for new functions/classes, integration
  tests for new endpoints, and update existing tests when behavior changes. Cover error paths.
- **Run tests before merging** to `main`; **build both images** before pushing image changes (unless
  told otherwise).
- **Portability:** never hardcode home-directory absolute paths; use relative paths or env vars.
- **Plan execution:** when executing a written implementation plan, ALWAYS use subagent-driven
  development (fresh implementer subagent per task + per-task spec/quality review + final
  whole-branch review). Do not ask the user which execution mode to use. This is their standing
  preference.
- **If a request contradicts these conventions, the architecture, or security posture, ask before
  implementing.** These patterns are intentional.

## Code patterns to follow

- **Config from env vars** with sensible defaults, all `VPN_SENTINEL_*` prefixed (`config.py`):
  `int(os.getenv("VPN_SENTINEL_SERVER_API_PORT", "5000"))`.
- **Structured logging** with component prefixes: `log_info("api", ...)`, `log_warn("security", ...)`,
  `log_error("telegram", ...)`.
- **Security middleware** runs `before_request` on API routes (rate limit 30 req/min/IP, optional IP
  allowlist). Health endpoints are public; sensitive API endpoints require the API key.
- **Background work** uses daemon threads (client monitoring, Telegram long-polling, stale cleanup).
- **External HTTP calls** must have retry/fallback. Geolocation uses a 3-provider cascade
  (ipinfo.io → ip-api.com → ipwhois.app), DNS uses Cloudflare with HTTP fallback. A single provider
  failing must not break the flow; degrade to `"Unknown"`.
- **Input validation:** sanitize all client-provided data (IPs, client IDs, locations); client IDs
  are kebab-case (`office-vpn-primary`).
- **Telegram messages:** HTML formatting with emojis and structured layout; watch for burst/rate
  limits.

## Code review checklist

- [ ] New state in `client_status` (or similar dicts) → lost on restart; document it
- [ ] New external HTTP calls → retry/fallback, no single point of failure
- [ ] Anything touching `client_status` → holds `client_status_lock` for read-modify-write
- [ ] New route module → imported in `server/__main__.py`, handler name added to `.vulture_allowlist.py`
- [ ] New/changed route path → derived from `API_PATH`, not a hardcoded `/api/v1`
- [ ] New Telegram notifications → can they burst? rate-limit if so
- [ ] Tests added, ≥80% coverage for new code
- [ ] `black --check --line-length 120 src/ tests/` and `flake8 --max-line-length=120 src/` both clean
- [ ] Shell changes → `shellcheck` and `shfmt -i 2 -ci` clean
- [ ] No home-directory paths or private IPs in the diff (the pre-commit hook rejects them)

## AI tooling in this repo

This project is maintained with **Claude Code**. The Claude configuration lives in `.claude/`
(skills, agents, slash commands, settings) and this `CLAUDE.md`. Project memory the team should see
goes in `.claude/memory/` (indexed by `MEMORY.md`). Other AI tools (Copilot, Codex, etc.) should read
this `CLAUDE.md` as their instruction file.
