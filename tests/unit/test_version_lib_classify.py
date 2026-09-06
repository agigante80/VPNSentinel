"""Direct tests for scripts/version-lib.sh's classify_version (issue #100, Part 4).

classify_version is the shared release primitive every release-automation lane sources
and acts on. It is documented as "close to pure": given a working version and a latest
tag, it prints exactly one verdict word (or fails closed on bad input). These tests call
the shell function DIRECTLY over synthetic inputs (never only in situ through a whole
release script), covering every documented verdict plus its two failure modes:

  first-release  no release tag exists yet
  ahead          working version > latest tag
  equal          working version == latest tag
  behind         working version < latest tag (regression, hard stop)
  <failure>      empty working version                 -> exit 2
  <failure>      non-semver working version or tag      -> exit 2

Run: pytest tests/unit/test_version_lib_classify.py -v
"""

import subprocess
from pathlib import Path

import pytest

# Locate the repo root relative to THIS file, never by an absolute path.
REPO_ROOT = Path(__file__).resolve().parents[2]
VERSION_LIB = REPO_ROOT / "scripts" / "version-lib.sh"


def classify_version(now, tag):
    """Source version-lib.sh in a fresh bash process and call classify_version(now, tag)
    directly, exactly as scripts/release-run.sh does, but without any of the git/tag
    machinery around it. Returns (returncode, stdout_verdict, stderr_text).

    version-lib.sh's own trailer only auto-runs (`git describe`, printing an extra
    verdict line) when `${BASH_SOURCE[0]} = ${0}`. Sourcing it as "$1" (never as "$0",
    which bash -c's own argv[0] placeholder occupies here) keeps BASH_SOURCE[0] and $0
    distinct, so only the explicit classify_version call below runs.
    """
    assert VERSION_LIB.exists(), f"version-lib.sh not found at {VERSION_LIB}"
    result = subprocess.run(
        ["bash", "-c", 'source "$1"; classify_version "$2" "$3"', "_", str(VERSION_LIB), now, tag],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def test_version_lib_exists_and_has_valid_bash_syntax():
    result = subprocess.run(["bash", "-n", str(VERSION_LIB)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, f"version-lib.sh syntax error: {result.stderr}"


# --- first-release: no tag exists yet -----------------------------------------------


def test_classify_first_release_no_tag():
    code, verdict, _ = classify_version("1.2.3", "")
    assert code == 0
    assert verdict == "first-release"


def test_classify_first_release_any_version_is_acceptable():
    # No tag means there is nothing to compare against: any semver working version
    # is a valid first release, including 0.0.1.
    code, verdict, _ = classify_version("0.0.1", "")
    assert code == 0
    assert verdict == "first-release"


# --- ahead: working version > latest tag --------------------------------------------


def test_classify_ahead_patch_bump():
    code, verdict, _ = classify_version("1.2.3", "1.2.0")
    assert code == 0
    assert verdict == "ahead"


def test_classify_ahead_minor_bump():
    code, verdict, _ = classify_version("2.0.0", "1.9.9")
    assert code == 0
    assert verdict == "ahead"


# --- equal: working version == latest tag -------------------------------------------


def test_classify_equal():
    code, verdict, _ = classify_version("1.2.3", "1.2.3")
    assert code == 0
    assert verdict == "equal"


def test_classify_equal_ignores_prerelease_suffix_on_working_version():
    # A prerelease build of an already-released core must read as `equal`, not `ahead`:
    # comparing release cores is what keeps sort -V from ranking 1.2.0-rc1 above 1.2.0
    # (documented at version-lib.sh:83-93).
    code, verdict, _ = classify_version("1.2.3-rc1", "1.2.3")
    assert code == 0
    assert verdict == "equal"


# --- behind: working version < latest tag (regression) -------------------------------


def test_classify_behind_patch():
    code, verdict, _ = classify_version("1.2.0", "1.2.3")
    assert code == 0
    assert verdict == "behind"


def test_classify_behind_major():
    code, verdict, _ = classify_version("1.9.9", "2.0.0")
    assert code == 0
    assert verdict == "behind"


# --- failure: empty working version ---------------------------------------------------


def test_classify_fails_closed_on_empty_working_version():
    code, verdict, stderr = classify_version("", "1.2.3")
    assert code == 2
    assert verdict == ""
    assert "could not read the working version" in stderr


# --- failure: non-semver values --------------------------------------------------------


def test_classify_fails_closed_on_non_semver_working_version():
    code, verdict, stderr = classify_version("not-a-version", "1.2.3")
    assert code == 2
    assert verdict == ""
    assert "not semver" in stderr


def test_classify_fails_closed_on_non_semver_tag():
    code, verdict, stderr = classify_version("1.2.3", "not-a-version")
    assert code == 2
    assert verdict == ""
    assert "not semver" in stderr


@pytest.mark.parametrize("bad_version", ["1.2", "v1.2.3", "1.2.3.4", "abc", "1.2.x"])
def test_classify_rejects_various_non_semver_shapes(bad_version):
    code, _, stderr = classify_version(bad_version, "1.2.3")
    assert code == 2
    assert "not semver" in stderr
