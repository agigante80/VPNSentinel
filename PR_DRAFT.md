PR draft: refactor/unified-architecture-per-file

Summary
-------
This branch migrates shared server- and client-related helper functionality into a single canonical Python package `vpn_sentinel_common/` and leaves small compatibility shims in `vpn_sentinel_server/` so existing imports/tests continue to work.

Goals
- Consolidate shared helpers into `vpn_sentinel_common/` as a canonical source-of-truth
- Preserve runtime/test compatibility via temporary shims in `vpn_sentinel_server/`
- Keep commits small and per-file to simplify review and revertability
- Do not push or open PR until maintainers approve (this draft is local-only)

Commits (ordered)
-----------------
The branch contains the following per-file commits (abbrev SHA + commit title). Each commit contains the single-file change that migrates that module into `vpn_sentinel_common` or provides a small compatibility fix.

- 4b6074d  chore(common): add vpn_sentinel_common.utils (migrated helpers)
  - Adds small utility helpers (json_escape, sanitize_string, etc.) previously in the client shell helpers.

- f279ed5  fix(logging): ensure logging prints to stdout for legacy tests
  - Adjusts `vpn_sentinel_common/logging.py` so log helpers also print friendly INFO/WARN/ERROR lines to stdout for tests that read process stdout.

- 13f0e5b  chore(common): add vpn_sentinel_common.security (migrated helpers)
  - Migrates access-control and rate-limiting helpers used by the server into the canonical package.

- fb8348d  chore(common): add vpn_sentinel_common.server_info (migrated helpers)
  - Adds get_server_public_ip and related helpers.

- 4720c8b  chore(common): add vpn_sentinel_common.telegram (migrated helpers)
  - Moves Telegram notification helper to the canonical package.

- 98e4dd0  chore(common): add vpn_sentinel_common.validation (migrated helpers)
  - Adds request/client validation helpers (client id, public ip, location validation).

- edeac7a  fix(client): print startup logs before launching health monitor so tests can capture them
  - Small, single-file fix to `vpn-sentinel-client/vpn-sentinel-client.sh` to ensure startup logs (Server, Client ID, Interval) are emitted before the health monitor is started (so tests reading stdout reliably find them).

Notes on compatibility
----------------------
- `vpn_sentinel_server/` contains small deprecation shims that import and re-export from `vpn_sentinel_common` and emit DeprecationWarning. This preserves imports used by tests and any external callers while the migration completes.

- The client runtime has been made "Python-first": runtime shell functions call into the Python shims if Python is available; legacy shell libs are kept only for unit tests that inspect script contents.

Testing performed
-----------------
- Grep/unit test compatibility checks during refactor.
- Full test suite run locally: all tests passing (final run: 202 passed, 52 skipped).
- Focused integration test fixes: moved client startup logs so integration helpers can capture the expected lines.

Checklist before pushing
------------------------
- [ ] Confirm maintainers reviewed the PR draft content and commit split
- [ ] Optionally run integration smoke with Docker Compose locally (`docker compose up --build` or `docker compose -f <compose-file> up`) to validate containers
- [ ] Decide timeline to remove `vpn_sentinel_server/` shims in a follow-up PR once consumers are updated
- [ ] Update docs and CHANGELOG with migration rationale and removal plan

How to review locally
---------------------
- Check out the branch locally: `git switch refactor/unified-architecture-per-file`
- Run unit tests: `pytest -q`
- Inspect each commit with `git show <sha>` or `git log -p <sha>` to see the file-level change

No remote actions performed: this draft is local-only and will not be pushed without explicit approval from the repo maintainers.

If you want I can:
- push this branch and open a draft PR on GitHub
- include more detailed per-file diffs inline in this PR draft
- run an optional Docker Compose integration smoke test and add results to the draft

-- end of draft
