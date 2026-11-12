"""Guards keeping the docs and the code in step on environment variable names (issue #145).

The docs once named variables no code reads (VPN_SENTINEL_SERVER_URL in a client example, so
the client silently used its placeholder URL) and the code read variables the README never
documented.

Guards, each over a "world" dict (README text, docs text, collected src names, allowlist):
  src_to_readme   every variable the code reads appears in README.md as a whole token, or is
                  on the allowlist.
  docs_to_src     every VPN_SENTINEL_* / TELEGRAM_* token in the user-facing docs and .env.example
                  files (name_docs()) is read by the code (including derived *_FILE names), or is
                  on the allowlist or the compose-only list.
  allowlist       every allowlist and compose-only entry has a non-blank reason, and none is stale.
  links           every relative markdown link in the scanned docs resolves to a file tracked by
                  git (or a directory holding one), relative to the linking file's directory; the
                  #anchor is ignored. Checking git, not the disk, keeps a local run equal to CI: an
                  untracked or gitignored file (the root CLAUDE.md) exists locally but not in a clone.

The collector parses src/ with ast and never imports it (telegram.py reads env at import time).

Guard rules (CLAUDE.md): each guard has a mutation test proving it red, each mutation asserts
every OTHER guard still passes (assert_only_guard_fails), and each selector is asserted to match
something.
"""

import ast
import re
import subprocess
from pathlib import Path

from test_compose_files import REPO_ROOT
from test_readme_quickstart import read_text_tolerant
from test_release_workflow_guards import assert_only_guard_fails

import pytest

SRC = REPO_ROOT / "src" / "vpn_sentinel"
NAME_RE = re.compile(r"^(VPN_SENTINEL|TELEGRAM)_[A-Z0-9_]+$")
TOKEN_RE = re.compile(r"(?<![A-Z0-9_])(?:VPN_SENTINEL|TELEGRAM)_[A-Z0-9_]*[A-Z0-9](?![A-Z0-9_])")
LINK_RE = re.compile(r"\]\(([^)\s]+)\)")

# name -> reason. Names the code reads that README.md deliberately does not document.
ALLOWLIST = {
    "VPN_SENTINEL_TEST_CAPTURE_PATH": "test hook in payload.py, not a user setting",
    "VPN_SENTINEL_CLIENT_VERSION": (
        "internal override of the reported client version, which defaults to the package version"
    ),
}

# name -> reason. Names set in compose files and .env.example that the application never reads.
COMPOSE_ONLY = {
    "VPN_SENTINEL_SERVER_IP": "compose builds the client URL from it; gluetun's DNS cannot resolve service names",
    "VPN_SENTINEL_DOCKER_SUBNET": "compose network subnet, kept in step with the VPN firewall allowance",
}


def name_docs():
    """Repo-relative files whose variable names are checked against the code (docs_to_src)."""
    paths = [REPO_ROOT / "README.md", REPO_ROOT / ".env.example"]
    paths += sorted((REPO_ROOT / "docs").glob("*.md"))
    paths += sorted((REPO_ROOT / "docs" / "guides").glob("*.md"))
    paths += [REPO_ROOT / "src" / "vpn_sentinel" / "client" / "README.md"]
    paths += sorted((REPO_ROOT / "deployments").rglob("README.md"))
    paths += sorted((REPO_ROOT / "deployments").rglob(".env.example"))
    return [p.relative_to(REPO_ROOT).as_posix() for p in paths]


def token_present(name, text):
    return re.search(r"(?<![A-Z0-9_])" + re.escape(name) + r"(?![A-Z0-9_])", text) is not None


def doc_tokens(text):
    return {m.group(0) for m in TOKEN_RE.finditer(text)}


# ---------------------------------------------------------------------------------
# Collector
# ---------------------------------------------------------------------------------


def collect_names(src_root=SRC):
    """Every VPN_SENTINEL_* / TELEGRAM_* string constant under src_root, plus `<arg>_FILE` for
    each read_secret(arg) call (arg a literal or a module-level string constant)."""
    names = set()
    for path in sorted(Path(src_root).rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        consts = {}
        for node in tree.body:
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                consts[node.targets[0].id] = node.value.value
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and NAME_RE.match(node.value):
                names.add(node.value)
            if isinstance(node, ast.Call):
                func = node.func
                fname = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
                if fname == "read_secret" and node.args:
                    arg = node.args[0]
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        base = arg.value
                    elif isinstance(arg, ast.Name):
                        base = consts.get(arg.id)
                    else:
                        base = None
                    if base and NAME_RE.match(base):
                        names.add(base)
                        names.add(base + "_FILE")
    return names


# ---------------------------------------------------------------------------------
# Reading the repository
# ---------------------------------------------------------------------------------


def link_files():
    """Repo-relative markdown files whose relative links are checked."""
    paths = [REPO_ROOT / "README.md"]
    paths += sorted((REPO_ROOT / "docs").glob("*.md"))
    paths += sorted((REPO_ROOT / "docs" / "guides").glob("*.md"))
    paths += [REPO_ROOT / "docs" / "architecture" / "README.md"]
    paths += [REPO_ROOT / "src" / "vpn_sentinel" / "client" / "README.md"]
    paths += sorted((REPO_ROOT / "deployments").rglob("README.md"))
    return [p.relative_to(REPO_ROOT).as_posix() for p in paths]


def tracked_paths(root=REPO_ROOT):
    """Every path git tracks, plus each of their parent directories, repo-relative."""
    out = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True).stdout
    paths = set()
    for rel in out.decode("utf-8").split("\0"):
        if not rel:
            continue
        paths.add(rel)
        parent = Path(rel).parent
        while parent != Path("."):
            paths.add(parent.as_posix())
            parent = parent.parent
    return paths


def real_world():
    docs = {}
    for rel in set(name_docs()) | set(link_files()):
        docs[rel] = read_text_tolerant(REPO_ROOT / rel)
    return {
        "names": collect_names(),
        "docs": docs,
        "allowlist": dict(ALLOWLIST),
        "compose_only": dict(COMPOSE_ONLY),
        "root": REPO_ROOT,
        "tracked": tracked_paths(),
    }


def mutate(world, rel, fn):
    """Copy of world with docs[rel] replaced by fn(text); the mutation must change something."""
    new = dict(world)
    new["docs"] = dict(world["docs"])
    new["docs"][rel] = fn(world["docs"][rel])
    assert new["docs"][rel] != world["docs"][rel], "mutation must actually change the text"
    return new


# ---------------------------------------------------------------------------------
# Guards: take a world, return a list of problems (empty = pass)
# ---------------------------------------------------------------------------------


def missing_from_readme(world):
    readme = world["docs"]["README.md"]
    return sorted(n for n in world["names"] if n not in world["allowlist"] and not token_present(n, readme))


def unknown_in_docs(world):
    known = set(world["names"]) | set(world["allowlist"]) | set(world["compose_only"])
    unknown = set()
    for rel in name_docs():
        unknown |= doc_tokens(world["docs"][rel]) - known
    return sorted(unknown)


def allowlist_problems(world):
    problems = []
    all_text = "\n".join(t for t in world["docs"].values() if t)
    for name, reason in {**world["allowlist"], **world["compose_only"]}.items():
        if not (reason or "").strip():
            problems.append(f"{name}: reason is empty")
        if name not in world["names"] and not token_present(name, all_text):
            problems.append(f"{name}: stale, no longer read in src and not in any scanned doc")
    return problems


def broken_links(world):
    root = world["root"]
    broken = []
    for rel, text in world["docs"].items():
        if rel not in link_files_of(world):
            continue
        for target in LINK_RE.findall(text or ""):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            path = target.split("#", 1)[0]
            if not path:
                continue
            target_path = (root / Path(rel).parent / path).resolve()
            try:
                target_rel = target_path.relative_to(root.resolve()).as_posix()
            except ValueError:
                target_rel = None  # points outside the repository
            if target_rel not in world["tracked"] and target_rel != ".":
                broken.append(f"{rel}: {target}")
    return sorted(broken)


def link_files_of(world):
    return world.get("link_files") or set(link_files())


GUARDS = {
    "src_to_readme": lambda w: not missing_from_readme(w),
    "docs_to_src": lambda w: not unknown_in_docs(w),
    "allowlist": lambda w: not allowlist_problems(w),
    "links": lambda w: not broken_links(w),
}

# ---------------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def world():
    return real_world()


class TestCollector:
    def test_real_src_has_spot_names_and_floor(self, world):
        names = world["names"]
        for spot in (
            "VPN_SENTINEL_APPRISE_URLS",
            "VPN_SENTINEL_APPRISE_URLS_FILE",
            "VPN_SENTINEL_INTERVAL",
            "VPN_SENTINEL_DEBUG",
        ):
            assert spot in names
        assert len(names) >= 30

    def test_read_secret_derives_file_name_only_for_secrets(self, tmp_path):
        (tmp_path / "a.py").write_text('NAME = "VPN_SENTINEL_Y"\nread_secret(NAME)\n')
        (tmp_path / "b.py").write_text('import os\nos.getenv("VPN_SENTINEL_LOG_FILE")\n')
        names = collect_names(tmp_path)
        assert {"VPN_SENTINEL_Y", "VPN_SENTINEL_Y_FILE", "VPN_SENTINEL_LOG_FILE"} <= names
        assert "VPN_SENTINEL_LOG_FILE_FILE" not in names

    def test_read_secret_literal_argument(self, tmp_path):
        (tmp_path / "a.py").write_text('cfg.read_secret("TELEGRAM_BOT_TOKEN")\n')
        assert collect_names(tmp_path) == {"TELEGRAM_BOT_TOKEN", "TELEGRAM_BOT_TOKEN_FILE"}


class TestRealDocs:
    def test_every_guard_passes_on_real_docs(self, world):
        assert missing_from_readme(world) == []
        assert unknown_in_docs(world) == []
        assert allowlist_problems(world) == []
        assert broken_links(world) == []

    def test_selectors_match_something(self, world):
        assert doc_tokens(world["docs"]["README.md"]), "README must contain variable tokens"
        assert doc_tokens(world["docs"]["docs/ARCHITECTURE.md"]), "ARCHITECTURE must contain variable tokens"
        assert LINK_RE.findall(world["docs"]["README.md"]), "README must contain links"
        assert len(link_files()) >= 8
        assert len(name_docs()) >= 15
        for rel in (".env.example", "deployments/server-central/.env.example", "src/vpn_sentinel/client/README.md"):
            assert doc_tokens(world["docs"][rel]), f"{rel} must contain variable tokens"


class TestMutations:
    def test_readme_missing_whole_token_metrics_token(self, world):
        mutated = mutate(
            world,
            "README.md",
            lambda t: re.sub(r"(?<![A-Z0-9_])VPN_SENTINEL_METRICS_TOKEN(?![A-Z0-9_])", "REDACTED", t),
        )
        assert token_present("VPN_SENTINEL_METRICS_TOKEN_FILE", mutated["docs"]["README.md"])
        assert missing_from_readme(mutated) == ["VPN_SENTINEL_METRICS_TOKEN"]
        assert_only_guard_fails(mutated, "src_to_readme", guards=GUARDS)

    def test_apprise_file_spelled_only_as_suffix(self, world):
        mutated = mutate(
            world,
            "README.md",
            lambda t: re.sub(r"(?<![A-Z0-9_])VPN_SENTINEL_APPRISE_URLS_FILE(?![A-Z0-9_])", "(or `_FILE`)", t),
        )
        assert missing_from_readme(mutated) == ["VPN_SENTINEL_APPRISE_URLS_FILE"]
        assert_only_guard_fails(mutated, "src_to_readme", guards=GUARDS)

    def test_mapping_read_is_not_skipped(self, world, tmp_path):
        (tmp_path / "m.py").write_text('def f(cfg):\n    return cfg.get("VPN_SENTINEL_HIDDEN")\n')
        mutated = dict(world)
        mutated["names"] = collect_names(tmp_path)
        assert mutated["names"] == {"VPN_SENTINEL_HIDDEN"}
        assert missing_from_readme(mutated) == ["VPN_SENTINEL_HIDDEN"]

    def test_doc_names_unread_variable(self, world):
        mutated = mutate(
            world,
            "README.md",
            lambda t: t + "\n- VPN_SENTINEL_URL=a\n- VPN_SENTINEL_SERVER_URL=http://x\n",
        )
        assert unknown_in_docs(mutated) == ["VPN_SENTINEL_SERVER_URL"]
        assert_only_guard_fails(mutated, "docs_to_src", guards=GUARDS)

    def test_architecture_unread_variable_is_caught(self, world):
        mutated = mutate(world, "docs/ARCHITECTURE.md", lambda t: t + "\nVPN_SENTINEL_CHECK_INTERVAL\n")
        assert unknown_in_docs(mutated) == ["VPN_SENTINEL_CHECK_INTERVAL"]
        assert_only_guard_fails(mutated, "docs_to_src", guards=GUARDS)

    def test_env_example_unread_variable_is_caught(self, world):
        rel = "deployments/server-central/.env.example"
        mutated = mutate(world, rel, lambda t: t + "\nVPN_SENTINEL_SERVER_RATE_LIMIT_REQUESTS=30\n")
        assert unknown_in_docs(mutated) == ["VPN_SENTINEL_SERVER_RATE_LIMIT_REQUESTS"]
        assert_only_guard_fails(mutated, "docs_to_src", guards=GUARDS)

    def test_compose_only_blank_reason(self, world):
        mutated = dict(world)
        mutated["compose_only"] = {**world["compose_only"], "VPN_SENTINEL_SERVER_IP": ""}
        assert allowlist_problems(mutated) == ["VPN_SENTINEL_SERVER_IP: reason is empty"]
        assert_only_guard_fails(mutated, "allowlist", guards=GUARDS)

    def test_allowlist_blank_reason(self, world):
        mutated = dict(world)
        mutated["allowlist"] = {**world["allowlist"], "VPN_SENTINEL_CLIENT_VERSION": "   "}
        assert allowlist_problems(mutated) == ["VPN_SENTINEL_CLIENT_VERSION: reason is empty"]
        assert_only_guard_fails(mutated, "allowlist", guards=GUARDS)

    def test_allowlist_stale_entry(self, world):
        mutated = dict(world)
        mutated["allowlist"] = {**world["allowlist"], "VPN_SENTINEL_GONE": "was a test hook"}
        problems = allowlist_problems(mutated)
        assert len(problems) == 1 and problems[0].startswith("VPN_SENTINEL_GONE: stale")
        assert_only_guard_fails(mutated, "allowlist", guards=GUARDS)

    def test_broken_relative_link(self, world):
        mutated = mutate(world, "README.md", lambda t: t + "\n[x](docs/DOES_NOT_EXIST.md)\n")
        assert broken_links(mutated) == ["README.md: docs/DOES_NOT_EXIST.md"]
        assert_only_guard_fails(mutated, "links", guards=GUARDS)

    def test_link_resolves_relative_to_linking_file(self, world):
        # docs/README.md linking to ARCHITECTURE.md (same dir) resolves; the same text in the root
        # README would not.
        text = "\n[a](ARCHITECTURE.md)\n"
        ok = mutate(world, "docs/README.md", lambda t: t + text)
        assert broken_links(ok) == []
        bad = mutate(world, "README.md", lambda t: t + text)
        assert broken_links(bad) == ["README.md: ARCHITECTURE.md"]

    def test_untracked_file_link_is_broken(self, world, tmp_path):
        # The root CLAUDE.md is gitignored: present on a maintainer's disk, absent from a clone.
        mutated = mutate(world, "README.md", lambda t: t + "\n[c](CLAUDE.md)\n")
        assert broken_links(mutated) == ["README.md: CLAUDE.md"]
        assert_only_guard_fails(mutated, "links", guards=GUARDS)

    def test_tracked_paths_selector_matches_something(self, world):
        assert "README.md" in world["tracked"] and "docs" in world["tracked"]

    def test_directory_link_and_anchor_resolve(self, world):
        mutated = mutate(world, "README.md", lambda t: t + "\n[d](docs/#top) [e](docs/ARCHITECTURE.md#x)\n")
        assert broken_links(mutated) == []
