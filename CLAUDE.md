# CLAUDE.md — VPNSentinel

Project instructions for AI assistants (Claude Code and any other agentic tool). This file is the
single source of truth for how to work in this repo. A companion expert skill lives at
`.claude/skills/vpnsentinel/SKILL.md` — load it for deep architecture/operational questions.

## What this project is

VPNSentinel is a **distributed client-server VPN monitoring system**. It watches whether traffic is
actually routing through a VPN, detects DNS leaks, and sends Telegram alerts.

```
[VPN Client container]                 [VPN Server container]
  vpn-sentinel-client.py                 vpn-sentinel-server.py
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
| `vpn-sentinel-server/vpn-sentinel-server.py` | Server entry point (starts 3 Flask apps + cleanup thread) |
| `vpn-sentinel-client/vpn-sentinel-client.py` | Client entry point (keepalive loop, subprocess mgmt) |
| `src/vpn_sentinel/common/` | Shared library (~21 modules) — the bulk of the logic |
| `tests/` | `unit/`, `integration/`, `smoke/` + `run_tests.sh` |
| `deployments/` | 4 deployment modes (all-in-one, client-standalone, client-with-vpn, server-central) |
| `docs/` | Architecture, security, testing, Telegram docs |
| `.github/workflows/ci-cd.yml` | CI/CD pipeline |

## Commands (verified against CI and tooling)

```bash
# Tests — full suite (installs deps, runs unit + integration, coverage, cleanup)
./tests/run_tests.sh --all
./tests/run_tests.sh --unit          # unit only
./tests/run_tests.sh --integration   # integration (needs running server)

# Tests — direct (what CI runs for unit)
python -m pytest tests/unit/ --tb=short --cov=vpn_sentinel.common --cov-report=term

# Lint (CI uses a syntax-error subset; full PEP8 check is max-line-length 120)
flake8 vpn-sentinel-server/ src/vpn_sentinel/common/ --select=E9,F63,F7,F82 --show-source --statistics
flake8 --max-line-length=120 src/vpn_sentinel/common/

# Build images (Dockerfiles build from repo root context)
docker build -t vpn-sentinel-server:latest -f vpn-sentinel-server/Dockerfile .
docker build -t vpn-sentinel-client:latest -f vpn-sentinel-client/Dockerfile .

# Run the stack
docker compose up -d
docker compose logs -f vpn-sentinel-server
```

Coverage gate is **80%** (`pyproject.toml`). Python **3.12** in CI (`requires-python >=3.10`).

## Working agreements

- **Branch:** Active development happens on `develop`. `main` is the release branch. Don't commit
  directly to `main`.
- **Commit/push only when asked.** When you do commit, end the message with the Co-Authored-By
  trailer for the model in use.
- **Tests are required** for new functionality — unit tests for new functions/classes, integration
  tests for new endpoints, and update existing tests when behavior changes. Cover error paths.
- **Run tests before merging** to `main`; **build both images** before pushing image changes (unless
  told otherwise).
- **Portability:** never hardcode `/home/$USER` absolute paths — use relative paths or env vars.
- **Plan execution:** when executing a written implementation plan, ALWAYS use subagent-driven
  development (fresh implementer subagent per task + per-task spec/quality review + final
  whole-branch review). Do not ask the user which execution mode to use — this is their standing
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
- **External HTTP calls** must have retry/fallback — geolocation uses a 3-provider cascade
  (ipinfo.io → ip-api.com → ipwhois.app), DNS uses Cloudflare with HTTP fallback. A single provider
  failing must not break the flow; degrade to `"Unknown"`.
- **Input validation:** sanitize all client-provided data (IPs, client IDs, locations); client IDs
  are kebab-case (`office-vpn-primary`).
- **Telegram messages:** HTML formatting with emojis and structured layout; watch for burst/rate
  limits.

## Code review checklist

- [ ] New state in `client_status` (or similar dicts) → lost on restart; document it
- [ ] New external HTTP calls → retry/fallback, no single point of failure
- [ ] Flask handlers touching shared `client_status` → thread safety
- [ ] New Telegram notifications → can they burst? rate-limit if so
- [ ] Tests added, ≥80% coverage for new code
- [ ] flake8 clean (max line length 120)

## AI tooling in this repo

This project is maintained with **Claude Code**. The Claude configuration lives in `.claude/`
(skills, agents, slash commands, settings) and this `CLAUDE.md`. Project memory the team should see
goes in `.claude/memory/` (indexed by `MEMORY.md`). Other AI tools (Copilot, Codex, etc.) should read
this `CLAUDE.md` as their instruction file.
