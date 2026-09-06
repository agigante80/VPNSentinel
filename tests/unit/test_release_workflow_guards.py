"""Structural guards over .github/workflows/auto-release.yml (issue #100).

The auto-release lane cannot be executed from the unit suite, so instead of testing
behaviour we assert INVARIANTS over the workflow's DEFINITION, parsed with PyYAML (never a
hand-rolled parser, never regex alone for structure), so a PR that quietly weakens the lane
fails CI instead of failing in production.

Six invariants, each mapped to a documented gotcha in this repo:
  1. checkout authenticates with secrets.ACTIONS_PUSH_TOKEN, not GITHUB_TOKEN
     (a tag pushed with GITHUB_TOKEN does not trigger tag-based workflows)
  2. checkout sets fetch-depth: 0 and fetch-tags: true
     (version-lib.sh's latest_tag sees nothing otherwise; every release looks like
     first-release and an existing version could be re-cut)
  3. VERSION_SOURCE: git is set EXPLICITLY in the job env (must not rely on the
     library default, already changed once - #88)
  4. the workflow_run trigger is filtered to branches: [main]
     (otherwise the lane can fire from other branches)
  5. the job is gated on `workflow_run.conclusion == 'success'`
     (otherwise a failed pipeline can cut a release)
  6. the Part 1 SHA assertion (git rev-parse HEAD == workflow_run.head_sha) is present
     and sits between the checkout step and the release step

Every guard below is mutation-tested (Part 3): each invariant has a fixture with that
invariant broken, and the test proves the SPECIFIC guard rejects it. A guard never observed
failing is decoration, not a guard. Where a guard uses a selector (find the checkout step,
find the release step, ...), a non-vacuity assertion proves the selector actually found
something on the compliant fixture, so the guard cannot be passing by matching nothing.

Guards are pure functions of a parsed workflow dict (or its `steps` list) so a mutated
fixture can be fed to them directly, mirroring the reference implementation's approach
(actual-mcp-server's tests/unit/workflow_release_guards.test.js).

This file also carries one guard over a second workflow, .github/workflows/ci-cd.yml
(issue #96): the step that actually publishes images (selected by BEHAVIOUR - a
docker/build-push-action step with push: true - not by job or step name, so a rename
or a newly added publishing step stays covered) must carry both sbom: true and
provenance: mode=max. Nothing else stops someone quietly deleting those two lines.
It uses its own guard registry (CI_CD_GUARDS) and its own parsed fixture (CI_CD_REAL),
kept separate from the auto-release ones above: the two workflows have unrelated job
shapes, so running the auto-release guards against ci-cd.yml (or vice versa) would
only ever report "job not found" noise, never a meaningful pass/fail.

Run: pytest tests/unit/test_release_workflow_guards.py -v
"""

import copy
from pathlib import Path

import yaml

# Locate the repo root relative to THIS file, never by an absolute path, so the test
# works regardless of where the repo is checked out.
REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "auto-release.yml"
JOB_NAME = "auto-release"

# ci-cd.yml (issue #96): a second, unrelated workflow guarded by this same file.
CI_CD_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci-cd.yml"


def _read_workflow_text():
    return WORKFLOW_PATH.read_text()


def _parse(text):
    return yaml.safe_load(text)


# ---------------------------------------------------------------------------------
# Pure guard functions - each takes a PARSED workflow dict and returns True/False.
# ---------------------------------------------------------------------------------


def get_on_block(workflow):
    """Return the `on:` trigger block.

    PyYAML's safe_load follows the YAML 1.1 spec, under which the bare scalar `on`
    (unquoted) parses as the boolean True rather than the string "on" (the well known
    "Norway problem": on/off/yes/no/true/false all parse as booleans). A guard that
    only ever looked up workflow["on"] would silently see an empty dict and pass
    vacuously on every real workflow file. Handle both keys so that never happens.
    """
    return workflow.get("on") or workflow.get(True) or {}


def get_jobs(workflow):
    return workflow.get("jobs") or {}


def get_job(workflow, job_name=JOB_NAME):
    return get_jobs(workflow).get(job_name) or {}


def get_steps(workflow, job_name=JOB_NAME):
    return get_job(workflow, job_name).get("steps") or []


def find_checkout_step(steps):
    for step in steps:
        if isinstance(step, dict) and str(step.get("uses", "")).startswith("actions/checkout"):
            return step
    return None


def find_step_index(steps, predicate):
    for i, step in enumerate(steps):
        if isinstance(step, dict) and predicate(step):
            return i
    return None


def _run_text(step):
    return str(step.get("run", "")) if isinstance(step, dict) else ""


def _is_checkout(step):
    return isinstance(step, dict) and str(step.get("uses", "")).startswith("actions/checkout")


def _is_sha_assertion(step):
    if not isinstance(step, dict):
        return False
    env = step.get("env") or {}
    expected_sha = str(env.get("EXPECTED_SHA", ""))
    return "head_sha" in expected_sha and "git rev-parse HEAD" in _run_text(step)


def _is_release_step(step):
    return "release-run.sh" in _run_text(step)


# --- Invariant 1 -------------------------------------------------------------------
def checkout_uses_push_token(workflow):
    """The checkout step must authenticate with secrets.ACTIONS_PUSH_TOKEN."""
    step = find_checkout_step(get_steps(workflow))
    if step is None:
        return False
    token = str((step.get("with") or {}).get("token", ""))
    return token == "${{ secrets.ACTIONS_PUSH_TOKEN }}"


# --- Invariant 2 -------------------------------------------------------------------
def checkout_fetches_full_history_and_tags(workflow):
    """The checkout step must fetch full history and tags."""
    step = find_checkout_step(get_steps(workflow))
    if step is None:
        return False
    with_block = step.get("with") or {}
    return with_block.get("fetch-depth") == 0 and with_block.get("fetch-tags") is True


# --- Invariant 3 -------------------------------------------------------------------
def version_source_is_explicit_git(workflow):
    """VERSION_SOURCE=git must be set explicitly in the job env, not left to the
    library default."""
    env = get_job(workflow).get("env") or {}
    return env.get("VERSION_SOURCE") == "git"


# --- Invariant 4 -------------------------------------------------------------------
def workflow_run_filtered_to_main(workflow):
    """The workflow_run trigger must be filtered to branches: [main]."""
    workflow_run = get_on_block(workflow).get("workflow_run") or {}
    return workflow_run.get("branches") == ["main"]


# --- Invariant 5 -------------------------------------------------------------------
def gated_on_workflow_run_success(workflow):
    """The job must only run when the upstream workflow_run concluded successfully."""
    condition = str(get_job(workflow).get("if", ""))
    return "workflow_run.conclusion" in condition and "success" in condition


# --- Invariant 6 -------------------------------------------------------------------
def sha_assertion_precedes_release(workflow):
    """The Part 1 SHA assertion must exist and sit strictly between the checkout step
    and the step that runs release-run.sh."""
    steps = get_steps(workflow)
    checkout_idx = find_step_index(steps, _is_checkout)
    assertion_idx = find_step_index(steps, _is_sha_assertion)
    release_idx = find_step_index(steps, _is_release_step)
    if checkout_idx is None or assertion_idx is None or release_idx is None:
        return False
    return checkout_idx < assertion_idx < release_idx


# --- ci-cd.yml guard (issue #96) ----------------------------------------------------
def find_publish_step(workflow):
    """Find the step, across ALL jobs, that actually publishes an image: a
    docker/build-push-action step with push: true.

    Selected by BEHAVIOUR, not by job or step name. ci-cd.yml has three
    docker/build-push-action steps (docker-test-build and security-scan both build
    with push: false so they can load and scan locally; only the docker-publish job's
    step pushes), and this deliberately does not hardcode "docker-publish" or "Build
    and push" as a name, so a renamed job or a newly added publishing step is still
    covered, and the two push: false steps are excluded by what they DO rather than
    by an exclusion list of names.
    """
    for job in get_jobs(workflow).values():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps") or []:
            if not isinstance(step, dict):
                continue
            if not str(step.get("uses", "")).startswith("docker/build-push-action"):
                continue
            if (step.get("with") or {}).get("push") is True:
                return step
    return None


def publish_step_has_sbom_and_max_provenance(workflow):
    """The step that actually pushes images must carry both sbom: true and
    provenance: mode=max (issue #96). Both are required together: an SBOM without
    full provenance, or provenance without an SBOM, does not answer the ticket's CVE
    scenario, which needs the package list attested."""
    step = find_publish_step(workflow)
    if step is None:
        return False
    with_block = step.get("with") or {}
    return with_block.get("sbom") is True and with_block.get("provenance") == "mode=max"


# ---------------------------------------------------------------------------------
# Fixtures: the real (compliant) workflow, and mutated (broken) copies used to prove
# each guard can actually fail. Mutations operate on the raw TEXT (mirroring the
# reference implementation) so each remains valid, parseable YAML, then are parsed
# with PyYAML like the real file.
# ---------------------------------------------------------------------------------


REAL_TEXT = _read_workflow_text()
REAL = _parse(REAL_TEXT)

CI_CD_TEXT = CI_CD_WORKFLOW_PATH.read_text()
CI_CD_REAL = _parse(CI_CD_TEXT)


def mutate(old, new, source=None):
    """Apply one string replacement to the real workflow text and return the parsed
    result. Asserts the replacement actually matched something, or the mutation
    fixture would silently test nothing."""
    text = source if source is not None else REAL_TEXT
    assert old in text, f"mutation anchor not found in workflow text: {old!r}"
    mutated_text = text.replace(old, new, 1)
    assert mutated_text != text, "mutation must actually change the workflow text"
    return _parse(mutated_text)


# Every guard, named, so a negative test can assert "this one fails and ALL FIVE
# OTHERS still pass" in one call. Registering here also means a future guard added
# to this module without a matching entry (and therefore without the non-interference
# check below covering it) is a visible, deliberate omission rather than a silent gap.
GUARDS = {
    "invariant_1_push_token": checkout_uses_push_token,
    "invariant_2_fetch_full_history": checkout_fetches_full_history_and_tags,
    "invariant_3_version_source_git": version_source_is_explicit_git,
    "invariant_4_branch_filter": workflow_run_filtered_to_main,
    "invariant_5_success_gate": gated_on_workflow_run_success,
    "invariant_6_sha_assertion_order": sha_assertion_precedes_release,
}

# ci-cd.yml (issue #96) has its own registry, kept separate from GUARDS above: the two
# workflows have unrelated job shapes, so a guard from one registry evaluated against
# the other workflow's parsed dict would only ever report "job not found", never a
# meaningful pass/fail.
CI_CD_GUARDS = {
    "publish_step_sbom_and_max_provenance": publish_step_has_sbom_and_max_provenance,
}


def assert_only_guard_fails(workflow, failing_guard, guards=None):
    """Assert that exactly ONE guard, `failing_guard`, rejects `workflow`, and every
    other registered guard still accepts it.

    This is the cross-check the ticket's Part 3 and its fourth Given/When/Then
    scenario require ("confirm no other guard fails"): a guard that fires on every
    mutation is exactly as useless as one that never fires on any, and asserting only
    the targeted guard's own False result (as a first pass of these tests did) cannot
    tell the two apart. Nothing else in this suite would catch a guard drifting into
    "rejects everything."

    `guards` selects which registry to cross-check against; it defaults to GUARDS
    (the auto-release invariants) so every existing call site is unaffected, but a
    mutated ci-cd.yml fixture must pass CI_CD_GUARDS here instead, or this would
    compare it against auto-release guards operating on a workflow that has no
    auto-release job at all.
    """
    registry = GUARDS if guards is None else guards
    assert failing_guard in registry, f"unknown guard name: {failing_guard!r}"
    results = {name: fn(workflow) for name, fn in registry.items()}
    assert results[failing_guard] is False, f"{failing_guard} was expected to reject this fixture but accepted it"
    collateral = {name: r for name, r in results.items() if name != failing_guard and r is not True}
    assert not collateral, (
        f"mutation aimed at {failing_guard} also broke unrelated guard(s): {collateral} " f"(full results: {results})"
    )


# ===================================================================================
# Non-vacuity: prove each guard's selector actually finds something on the real,
# compliant workflow before trusting a negative result on a mutated copy.
# ===================================================================================


def test_non_vacuous_selectors():
    steps = get_steps(REAL)
    assert steps, "auto-release job must have steps, or every guard here is vacuous"
    assert (
        find_checkout_step(steps) is not None
    ), "a checkout step must exist, or guards 1 and 2 (token, fetch-depth/tags) are vacuous"
    assert (
        find_step_index(steps, _is_sha_assertion) is not None
    ), "the SHA-assertion step must exist, or guard 6 is vacuous"
    assert (
        find_step_index(steps, _is_release_step) is not None
    ), "the release-run.sh step must exist, or guard 6 is vacuous"
    assert (
        get_on_block(REAL).get("workflow_run") is not None
    ), "the on.workflow_run trigger must exist, or guard 4 is vacuous"
    assert get_job(REAL) != {}, "the auto-release job must exist, or guards 3 and 5 are vacuous"


def test_non_vacuous_selector_ci_cd_publish_step():
    assert find_publish_step(CI_CD_REAL) is not None, (
        "ci-cd.yml must have a docker/build-push-action step with push: true, "
        "or the sbom/provenance guard (issue #96) is vacuous"
    )


# ===================================================================================
# Positive: each invariant holds over the real, currently-committed workflow.
# ===================================================================================


def test_invariant_1_checkout_uses_push_token_positive():
    assert checkout_uses_push_token(REAL) is True


def test_invariant_2_checkout_fetches_full_history_positive():
    assert checkout_fetches_full_history_and_tags(REAL) is True


def test_invariant_3_version_source_explicit_git_positive():
    assert version_source_is_explicit_git(REAL) is True


def test_invariant_4_workflow_run_filtered_to_main_positive():
    assert workflow_run_filtered_to_main(REAL) is True


def test_invariant_5_gated_on_workflow_run_success_positive():
    assert gated_on_workflow_run_success(REAL) is True


def test_invariant_6_sha_assertion_precedes_release_positive():
    assert sha_assertion_precedes_release(REAL) is True


def test_ci_cd_publish_step_has_sbom_and_max_provenance_positive():
    assert publish_step_has_sbom_and_max_provenance(CI_CD_REAL) is True


# ===================================================================================
# Negative (mutation-tested): each invariant's guard must reject a broken copy, and
# ONLY that guard's own concern - the other five guards must still pass on it.
# ===================================================================================


def test_invariant_1_negative_github_token_swap():
    mutated = mutate(
        "fetch-tags: true\n          token: ${{ secrets.ACTIONS_PUSH_TOKEN }}",
        "fetch-tags: true\n          token: ${{ secrets.GITHUB_TOKEN }}",
    )
    assert_only_guard_fails(mutated, "invariant_1_push_token")


def test_invariant_1_negative_token_missing():
    mutated = mutate(
        "          fetch-tags: true\n          token: ${{ secrets.ACTIONS_PUSH_TOKEN }}\n",
        "          fetch-tags: true\n",
    )
    assert_only_guard_fails(mutated, "invariant_1_push_token")


def test_invariant_2_negative_fetch_depth_missing():
    mutated = mutate(
        "          ref: ${{ github.event.workflow_run.head_sha }}\n          fetch-depth: 0\n",
        "          ref: ${{ github.event.workflow_run.head_sha }}\n",
    )
    assert_only_guard_fails(mutated, "invariant_2_fetch_full_history")


def test_invariant_2_negative_fetch_tags_false():
    mutated = mutate("fetch-tags: true", "fetch-tags: false")
    assert_only_guard_fails(mutated, "invariant_2_fetch_full_history")


def test_invariant_3_negative_version_source_missing():
    mutated = mutate("      VERSION_SOURCE: git\n", "")
    assert_only_guard_fails(mutated, "invariant_3_version_source_git")


def test_invariant_3_negative_version_source_wrong_value():
    mutated = mutate("VERSION_SOURCE: git", "VERSION_SOURCE: file")
    assert_only_guard_fails(mutated, "invariant_3_version_source_git")


def test_invariant_4_negative_branch_filter_removed():
    mutated = mutate("    branches: [main]\n", "")
    assert_only_guard_fails(mutated, "invariant_4_branch_filter")


def test_invariant_4_negative_branch_filter_widened():
    mutated = mutate("branches: [main]", "branches: [main, develop]")
    assert_only_guard_fails(mutated, "invariant_4_branch_filter")


def test_invariant_5_negative_success_gate_removed():
    mutated = mutate("    if: ${{ github.event.workflow_run.conclusion == 'success' }}\n", "")
    assert_only_guard_fails(mutated, "invariant_5_success_gate")


def test_invariant_5_negative_gate_weakened_to_always():
    mutated = mutate(
        "if: ${{ github.event.workflow_run.conclusion == 'success' }}",
        "if: ${{ always() }}",
    )
    assert_only_guard_fails(mutated, "invariant_5_success_gate")


def test_invariant_6_negative_assertion_step_removed():
    assertion_block = (
        "      # Fail-closed guard (issue #100): nothing else asserts that the checkout actually\n"
        "      # resolved to the commit CI went green on. If a future actions/checkout behaviour\n"
        "      # change (see #99) ever resolves a workflow_run + explicit-ref checkout to a\n"
        "      # different commit, this stops the lane before it tags the wrong commit and\n"
        "      # reports success, instead of silently mis-releasing.\n"
        "      - name: Assert the checkout is the commit CI went green on\n"
        "        env:\n"
        "          EXPECTED_SHA: ${{ github.event.workflow_run.head_sha }}\n"
        "        run: |\n"
        '          actual="$(git rev-parse HEAD)"\n'
        '          if [ "$actual" != "$EXPECTED_SHA" ]; then\n'
        '            echo "::error::Refusing to release. Checked out $actual but the green CI run was $EXPECTED_SHA."\n'
        "            exit 1\n"
        "          fi\n"
        '          echo "Checkout verified: $actual"\n\n'
    )
    mutated = mutate(assertion_block, "")
    assert_only_guard_fails(mutated, "invariant_6_sha_assertion_order")


def test_invariant_6_negative_assertion_moved_after_release():
    """Reordering (not removing) the assertion so it runs AFTER release-run.sh must
    also be rejected: a guard that only checked "does the step exist somewhere" would
    pass here, which is exactly the "could not fail" trap Part 3 warns about."""
    steps = copy.deepcopy(get_steps(REAL))
    checkout_idx = find_step_index(steps, _is_checkout)
    assertion_idx = find_step_index(steps, _is_sha_assertion)
    release_idx = find_step_index(steps, _is_release_step)
    assert checkout_idx is not None and assertion_idx is not None and release_idx is not None

    reordered = [steps[checkout_idx], steps[release_idx], steps[assertion_idx]]
    reordered_workflow = copy.deepcopy(REAL)
    reordered_workflow["jobs"][JOB_NAME]["steps"] = reordered

    assert_only_guard_fails(reordered_workflow, "invariant_6_sha_assertion_order")


def test_invariant_6_negative_expected_sha_not_head_sha():
    """The assertion must compare against workflow_run.head_sha specifically, not
    some other value that merely LOOKS like a guard (e.g. github.sha, which is the
    default branch tip for a workflow_run event, not the commit CI actually ran on)."""
    mutated = mutate(
        "EXPECTED_SHA: ${{ github.event.workflow_run.head_sha }}",
        "EXPECTED_SHA: ${{ github.sha }}",
    )
    assert_only_guard_fails(mutated, "invariant_6_sha_assertion_order")


def test_invariant_6_negative_missing_git_rev_parse():
    """A step that merely NAMES itself as the assertion, without actually running
    `git rev-parse HEAD`, must not satisfy the guard - naming is not doing."""
    mutated = mutate(
        'actual="$(git rev-parse HEAD)"',
        'actual="$GITHUB_SHA"',
    )
    assert_only_guard_fails(mutated, "invariant_6_sha_assertion_order")


def test_ci_cd_publish_step_negative_flags_removed_entirely():
    mutated = mutate(
        "          sbom: true\n          provenance: mode=max\n",
        "",
        source=CI_CD_TEXT,
    )
    assert_only_guard_fails(mutated, "publish_step_sbom_and_max_provenance", guards=CI_CD_GUARDS)


def test_ci_cd_publish_step_negative_sbom_removed_provenance_kept():
    mutated = mutate(
        "          sbom: true\n          provenance: mode=max\n",
        "          provenance: mode=max\n",
        source=CI_CD_TEXT,
    )
    assert_only_guard_fails(mutated, "publish_step_sbom_and_max_provenance", guards=CI_CD_GUARDS)


def test_ci_cd_publish_step_negative_provenance_downgraded_to_min():
    mutated = mutate("provenance: mode=max", "provenance: mode=min", source=CI_CD_TEXT)
    assert_only_guard_fails(mutated, "publish_step_sbom_and_max_provenance", guards=CI_CD_GUARDS)


def test_ci_cd_publish_step_negative_provenance_downgraded_to_bare_true():
    """provenance: true is a legal build-push-action input (the default-provenance
    behaviour), but it is not mode=max, and the guard must not be fooled by any
    truthy provenance value."""
    mutated = mutate("provenance: mode=max", "provenance: true", source=CI_CD_TEXT)
    assert_only_guard_fails(mutated, "publish_step_sbom_and_max_provenance", guards=CI_CD_GUARDS)


# ===================================================================================
# Sanity: the mutation helper itself must not be trivially satisfiable (it must
# really change the text and really be parseable YAML), and the real file must
# parse to a job that all six guards jointly pass at once (no guard is contradicted
# by another over the same real file).
# ===================================================================================


def test_all_six_invariants_hold_simultaneously_on_the_real_workflow():
    assert checkout_uses_push_token(REAL) is True
    assert checkout_fetches_full_history_and_tags(REAL) is True
    assert version_source_is_explicit_git(REAL) is True
    assert workflow_run_filtered_to_main(REAL) is True
    assert gated_on_workflow_run_success(REAL) is True
    assert sha_assertion_precedes_release(REAL) is True


def test_ci_cd_guard_holds_on_the_real_workflow():
    assert publish_step_has_sbom_and_max_provenance(CI_CD_REAL) is True
