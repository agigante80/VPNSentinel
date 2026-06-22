<!-- ci-health-version: 2 -->

# CI Health Monitor

Check all GitHub Actions workflows for failures, create P0 tickets (on agigante80/VPNSentinel), gate each ticket, and auto-fix safe failures.

## Process

Execute these phases in order. Stop early if all workflows are passing.

### Phase 1: Discover and assess workflows

Auto-discover all workflow files:

```bash
ls .github/workflows/*.yml .github/workflows/*.yaml 2>/dev/null
```

VPNSentinel has a single pipeline: `.github/workflows/ci-cd.yml`. Its jobs, in order, are:

- `generate-version` -- runs `get_version.sh`
- `lint` -- flake8 (select E9,F63,F7,F82 first, then full `--max-line-length=120`) and `black --check` (both are hard gates)
- `test` -- pytest unit tests with `--cov=vpn_sentinel.common --cov-fail-under=80`
- `integration-tests` -- integration suite (needs running server)
- `docker-test-build` -- builds both server and client images
- `build-and-publish` -- pushes images (runs only on `main`)
- `security-scan` -- scans server and client images
- CodeQL (`Analyze (python)` and `Analyze (actions)`) and Trivy and GitGuardian

**Known noise:** a "CodeQL" check sometimes fast-fails in ~4 seconds while the real `Analyze (python)` and `Analyze (actions)` jobs pass normally. This is a config artifact, not a code finding. Flag it in the summary as a config artifact and do not file a P0 for it.

Detect the main working branch:

```bash
git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "develop"
```

VPNSentinel uses `develop` for active development and `main` for releases. Check both branches if needed.

For each discovered workflow, check the latest run on the working branch:

```bash
gh run list --workflow <workflow-file> --branch <branch> --limit 1 --json databaseId,conclusion,createdAt,name -q '.[0]'
```

For each failing run, get failed jobs and error logs:

```bash
gh run view <RUN_ID> --json jobs --jq '.jobs[] | select(.conclusion == "failure") | .name'
gh run view <RUN_ID> --log-failed 2>&1 | tail -150
```

Report a summary table:

| Workflow | Branch | Status | Failed jobs |
|---|---|---|---|
| ci-cd.yml | develop | pass/fail | job1, job2 |
| ci-cd.yml | main | pass/fail | - |

If ALL workflows are passing, report "All workflows green" and stop.

**Classify governance workflows separately.** The `build-and-publish` job is a release gate that runs only on `main`. A failure there caused by a version bump being absent is an intentional governance signal (see `docs/versioning.md`), not a CI breakage. Do not file a P0 bug for it. Surface it as "action: bump the version per docs/versioning.md" and move on.

### Phase 2: Create tickets for failures

For each failing job, open issues on `agigante80/VPNSentinel`:

1. **Check for an existing open ticket** to avoid duplicates:
```bash
gh issue list --repo agigante80/VPNSentinel --search "fix(ci): <job-name-keyword>" --state open --limit 1
```

2. **If no ticket exists**, create one:
   - Title: `fix(ci): <workflow> - <job-name> failing on <branch>`
   - Labels: `bug`, `infrastructure`
   - Priority: P0
   - Body must include:
     - Error logs (last 100 lines of failed job)
     - Link to the failing run
     - Affected files (if identifiable from logs)
     - `<!-- template-version: 3 -->` marker
     - Acceptance criteria: "CI job passes on `<branch>`"
   - For lint failures: note which rule triggered (E9/F63/F7/F82 syntax gate or full PEP8 max-line-length 120)
   - For test failures: note the coverage percentage reported vs. the 80% gate on `vpn_sentinel.common`

3. **If a ticket already exists**, add a comment with the latest error logs.

### Phase 3: Gate each new ticket

Run the ticket-gate agent on each newly created ticket. Fix and re-run until 10/10.

Use parallel agents if multiple tickets were created.

### Phase 4: Implement fixes

For each gated ticket:

**AUTO-IMPLEMENT** (fix and push):
- Lint failures -- flake8 or black formatting errors in `src/`
- Unit test failures -- pytest failures in `tests/unit/`
- Coverage gate failures -- coverage on `vpn_sentinel.common` below 80%
- Build failures -- Docker build errors in server or client Dockerfile
- Dependency issues
- Configuration errors

After implementing, run the VPNSentinel lint and test commands:

```bash
flake8 src/ --select=E9,F63,F7,F82 --show-source --statistics
flake8 --max-line-length=120 src/
black --check src/
python -m pytest tests/unit/ --tb=short --cov=vpn_sentinel.common --cov-report=term --cov-fail-under=80
```

Then commit and push:

```bash
git add <specific-files>
git commit -m "fix(ci): <description>"
git push origin <branch>
```

**DO NOT AUTO-IMPLEMENT** (investigate only, leave a comment):
- Integration test failures -- comment: "Integration: investigation complete, manual review required before fix" (these require a running server and may need environment changes)
- Security scan findings from `security-scan`, Trivy, or GitGuardian -- comment with findings summary, do not auto-fix
- CodeQL fast-fail noise -- comment: "CodeQL config artifact: fast-fail check is a known noise pattern, real Analyze jobs pass" and close the ticket if opened in error
- Release / version-gate failures (`build-and-publish` on `main`) -- the version bump (patch/minor/major per `docs/versioning.md`) is the PR author's call. Never auto-bump to make the gate pass. Comment the required action.

### Phase 5: Verify

After pushing, wait 30 seconds then check whether a new run was triggered:

```bash
gh run list --workflow ci-cd.yml --branch <branch> --limit 1 --json databaseId,status,conclusion -q '.[0]'
```

Report whether the fix was pushed and a new run is in progress.

---

## Rules

- **Never hard-code workflow file names** -- always discover via `ls .github/workflows/`
- **Never hard-code branch names** -- always detect from git or ask the user; default working branch is `develop`
- **Gate review must pass 10/10** before implementing any fix
- **One commit per fix** -- not one big commit for everything
- **Only push to the working branch** -- never to `main` directly unless that is the working branch
- **No duplicate tickets** -- always search `agigante80/VPNSentinel` before creating
- **Coverage gate is 80% on `vpn_sentinel.common`** -- a drop below this is a hard failure, not a warning
- **Both lint gates must pass** -- the syntax-error subset (E9,F63,F7,F82) and the full PEP8 check (max-line-length 120)
- **CodeQL fast-fail is noise** -- do not file P0 bugs for the ~4s fast-fail check; the real Analyze jobs are the signal
