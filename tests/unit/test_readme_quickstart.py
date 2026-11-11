"""Guards over the README Quick Start and the Telegram variable names (issue #131).

The Quick Start once told users to set VPN_SENTINEL_TELEGRAM_BOT_TOKEN / _CHAT_ID (the code
reads TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID, so alerts were silently off) and to curl
localhost:18081 (a port no compose file publishes).

Three guards, each over a "world" dict (README text, .env.example names, published host ports,
text files to scan):
  env_names   every uncommented NAME= in the ```env fences of the Quick Start section is an
              uncommented NAME= line in root .env.example. The section runs from the
              `## Quick Start` heading to the next `## ` heading (not `### `).
  host_ports  every localhost:<port> / 127.0.0.1:<port> in the Quick Start code blocks, except
              on `docker compose exec` / `docker exec` lines, is a host port published by the
              resolved root compose (docker-dependent; CI sets VPN_SENTINEL_REQUIRE_DOCKER=1 for
              the whole tests/unit/ run, so it fails rather than skips there).
  wrong_names README.md, docs/**/*.md and deployments/** never mention the two wrong names.

Guard rules (CLAUDE.md): every guard has a mutation test proving it red, each mutation asserts
every OTHER guard still passes (assert_only_guard_fails), and each selector is asserted to match
something. The one mutation where two guards legitimately fire is asserted as that explicit pair.
"""

import re
from pathlib import Path

from test_compose_files import ROOT, REPO_ROOT, real
from test_release_workflow_guards import assert_only_guard_fails

import pytest

WRONG_NAMES = ("VPN_SENTINEL_TELEGRAM_BOT_TOKEN", "VPN_SENTINEL_TELEGRAM_CHAT_ID")
NAME_RE = re.compile(r"^([A-Z][A-Z0-9_]*)=")
PORT_RE = re.compile(r"(?:localhost|127\.0\.0\.1):(\d+)")
EXEC_PREFIXES = ("docker compose exec", "docker exec")

# ---------------------------------------------------------------------------------
# Reading the repository (text only: docs/ holds PNGs)
# ---------------------------------------------------------------------------------


def read_text_tolerant(path):
    """Decode-tolerant read. Returns None for binary files (NUL bytes)."""
    data = Path(path).read_bytes()
    if b"\x00" in data:
        return None
    return data.decode("utf-8", errors="replace")


def scanned_files():
    """{repo-relative path: text} for README.md, docs/**/*.md and deployments/** text files."""
    paths = [REPO_ROOT / "README.md"]
    paths += sorted((REPO_ROOT / "docs").rglob("*.md"))
    paths += sorted(p for p in (REPO_ROOT / "deployments").rglob("*") if p.is_file())
    files = {}
    for p in paths:
        text = read_text_tolerant(p)
        if text is not None:
            files[p.relative_to(REPO_ROOT).as_posix()] = text
    return files


def env_example_names(text):
    return {m.group(1) for m in (NAME_RE.match(line) for line in text.splitlines()) if m}


def published_ports(cfg):
    ports = set()
    for svc in cfg.get("services", {}).values():
        for p in svc.get("ports") or []:
            if p.get("published") is not None:
                ports.add(int(p["published"]))
    return ports


def quickstart_lines(readme):
    """Yield (line, fence_lang) for each line of the Quick Start section. Fence state is
    tracked so a `## ` inside a code block cannot end the section. fence_lang is None outside
    a fence. Empty when the heading is missing."""
    in_section = False
    fence = None  # None outside a fence, else the language string
    for line in readme.splitlines():
        stripped = line.strip()
        if fence is None and line.startswith("## "):
            if in_section:
                return
            in_section = line.strip() == "## Quick Start"
            continue
        if not in_section:
            continue
        if stripped.startswith("```"):
            fence = None if fence is not None else stripped[3:].strip()
            continue
        yield line, fence


def quickstart_env_names(readme):
    names = []
    for line, fence in quickstart_lines(readme):
        if fence == "env":
            m = NAME_RE.match(line)
            if m:
                names.append(m.group(1))
    return names


def quickstart_ports(readme):
    ports = []
    for line, fence in quickstart_lines(readme):
        if fence is None or line.strip().startswith(EXEC_PREFIXES):
            continue
        ports.extend(int(p) for p in PORT_RE.findall(line))
    return ports


# ---------------------------------------------------------------------------------
# Guards: take a world, return a list of error strings (empty = pass)
# ---------------------------------------------------------------------------------


def env_name_errors(world):
    names = quickstart_env_names(world["readme"])
    if len(names) < 2:
        return [f"env selector extracted {len(names)} names from the Quick Start env blocks, expected at least 2"]
    return [f"{n} is not defined in .env.example" for n in names if n not in world["env_example"]]


def host_port_errors(world):
    ports = quickstart_ports(world["readme"])
    if not ports:
        return ["port selector extracted no host ports from the Quick Start code blocks, expected at least 1"]
    return [f"port {p} is not published by compose.yaml" for p in ports if p not in world["ports"]]


def wrong_name_errors(world):
    scanned = {**world["files"], "README.md": world["readme"]}  # the readme under test, not the on-disk copy
    if len(scanned) < 10:
        return [f"wrong-name selector scanned {len(scanned)} files, expected at least 10"]
    return [f"{n} found in {rel}" for rel, text in scanned.items() for n in WRONG_NAMES if n in text]


ERRORS = {"env_names": env_name_errors, "host_ports": host_port_errors, "wrong_names": wrong_name_errors}
GUARDS = {name: (lambda w, fn=fn: not fn(w)) for name, fn in ERRORS.items()}


# ---------------------------------------------------------------------------------
# Fixtures and mutation helpers
# ---------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def world():
    files = scanned_files()
    return {
        "readme": files["README.md"],
        "env_example": env_example_names((REPO_ROOT / ".env.example").read_text(encoding="utf-8")),
        "ports": published_ports(real(ROOT)),
        "files": files,
    }


def replace_once(text, old, new):
    """One replacement; asserts the anchor exists so a mutation can never test nothing."""
    assert old in text, f"mutation anchor not found: {old!r}"
    mutated = text.replace(old, new, 1)
    assert mutated != text
    return mutated


def with_readme(world, old, new):
    return {**world, "readme": replace_once(world["readme"], old, new)}


ENV_ANCHOR = "VPN_SENTINEL_API_KEY=your-secure-api-key-here\n"
EXEC_LINE = "docker compose exec vpn-sentinel-server wget -qO- http://127.0.0.1:8081/health"


# ---------------------------------------------------------------------------------
# Real repository
# ---------------------------------------------------------------------------------


def test_real_repo_passes_all_guards(world):
    for name, fn in ERRORS.items():
        assert fn(world) == [], name


def test_non_vacuous_selectors(world):
    assert len(quickstart_env_names(world["readme"])) >= 2
    assert len(quickstart_ports(world["readme"])) >= 1
    assert len(world["files"]) >= 10
    assert 18080 in world["ports"] and 15000 in world["ports"], world["ports"]
    assert "TELEGRAM_BOT_TOKEN" in world["env_example"]
    # the scan set really covers all three trees, and skipped the PNGs
    rels = set(world["files"])
    assert "README.md" in rels
    assert any(r.startswith("docs/") for r in rels)
    assert any(r.startswith("deployments/") for r in rels)
    assert not any(r.endswith(".png") for r in rels)
    assert list((REPO_ROOT / "docs").rglob("*.png")), "decode-tolerance fixture: docs/ should hold PNGs"


def test_selectors_fail_when_they_match_nothing(world):
    no_section = {**world, "readme": "# Title\n\nNo quick start here.\n"}
    assert env_name_errors(no_section) and host_port_errors(no_section)
    assert wrong_name_errors({**world, "files": {"README.md": "x"}})


def test_binary_files_are_skipped(tmp_path):
    png = tmp_path / "a.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\xff\xfe")
    assert read_text_tolerant(png) is None
    latin = tmp_path / "b.md"
    latin.write_bytes(b"caf\xe9")
    assert read_text_tolerant(latin) is not None


# ---------------------------------------------------------------------------------
# Guard 1: env names
# ---------------------------------------------------------------------------------


def test_guard1_undefined_name_fails_only_env_names(world):
    w = with_readme(world, ENV_ANCHOR, ENV_ANCHOR + "VPN_SENTINEL_NOT_DEFINED=x\n")
    assert "VPN_SENTINEL_NOT_DEFINED is not defined in .env.example" in env_name_errors(w)
    assert_only_guard_fails(w, "env_names", guards=GUARDS)


def test_guard1_wrong_telegram_name_fires_exactly_env_names_and_wrong_names(world):
    # The only mutation where two guards legitimately fire: the wrong name is both an
    # undefined env name (guard 1) and a forbidden name (guard 3). Guard 2 must stay green.
    w = with_readme(world, ENV_ANCHOR, ENV_ANCHOR + "VPN_SENTINEL_TELEGRAM_BOT_TOKEN=x\n")
    results = {name: fn(w) for name, fn in GUARDS.items()}
    assert results == {"env_names": False, "host_ports": True, "wrong_names": False}, results
    assert "VPN_SENTINEL_TELEGRAM_BOT_TOKEN is not defined in .env.example" in env_name_errors(w)
    assert any("VPN_SENTINEL_TELEGRAM_BOT_TOKEN found in README.md" in e for e in wrong_name_errors(w))


def test_guard1_does_not_read_past_the_quick_start(world):
    readme = world["readme"]
    # the real README has a later-section env block with a name .env.example lacks
    assert "VPN_SENTINEL_TELEGRAM_ENABLED=true" in readme
    assert "VPN_SENTINEL_TELEGRAM_ENABLED" not in world["env_example"]
    assert "VPN_SENTINEL_TELEGRAM_ENABLED" not in quickstart_env_names(readme)
    assert env_name_errors(world) == []
    w = {**world, "readme": readme + "\n## Later\n\n```env\nUNKNOWN_VAR=x\n```\n"}
    assert env_name_errors(w) == []


def test_guard1_comments_blanks_and_non_env_fences_are_ignored(world):
    w = with_readme(
        world,
        ENV_ANCHOR,
        ENV_ANCHOR + "# COMMENTED_OUT=x\n\n   INDENTED_NOT_A_NAME=x\nlower_case=x\n```\n\n```bash\nBASH_ONLY=x\n",
    )
    assert env_name_errors(w) == []


def test_section_ends_at_next_h2_not_h3(world):
    names = quickstart_env_names(world["readme"])
    # "### 3." and "### 4." subsections are inside the section; a `## ` ends it
    assert "TELEGRAM_BOT_TOKEN" in names
    w = {**world, "readme": world["readme"] + "\n## Later\n\n```env\nUNKNOWN_VAR=x\n```\n"}
    assert quickstart_env_names(w["readme"]) == names


# ---------------------------------------------------------------------------------
# Guard 2: host ports
# ---------------------------------------------------------------------------------


def test_guard2_unpublished_port_fails_only_host_ports(world):
    w = with_readme(world, "http://localhost:18080/dashboard", "http://localhost:18081/health")
    assert "port 18081 is not published by compose.yaml" in host_port_errors(w)
    assert_only_guard_fails(w, "host_ports", guards=GUARDS)


def test_guard2_ignores_exec_lines(world):
    assert EXEC_LINE in world["readme"]
    assert 8081 not in quickstart_ports(world["readme"])
    assert 8081 not in world["ports"]
    assert host_port_errors(world) == []
    # leading whitespace is stripped before the prefix check, and plain `docker exec` counts
    w = with_readme(
        world, EXEC_LINE, "   " + EXEC_LINE + "\ndocker exec vpn-sentinel-server wget http://127.0.0.1:9999/x"
    )
    assert host_port_errors(w) == []
    assert_only_guard_fails(
        with_readme(world, EXEC_LINE, "curl http://127.0.0.1:8081/health"), "host_ports", guards=GUARDS
    )


def test_guard2_only_reads_code_blocks_of_the_quick_start(world):
    w = {**world, "readme": world["readme"] + "\n## Later\n\n```bash\ncurl http://localhost:1/x\n```\n"}
    assert host_port_errors(w) == []


# ---------------------------------------------------------------------------------
# Guard 3: wrong names nowhere
# ---------------------------------------------------------------------------------


def test_guard3_wrong_name_in_docs_fails_only_wrong_names(world):
    rel = "docs/ARCHITECTURE.md"
    assert rel in world["files"]
    files = {**world["files"], rel: world["files"][rel] + "\nVPN_SENTINEL_TELEGRAM_CHAT_ID=1\n"}
    w = {**world, "files": files}
    assert "VPN_SENTINEL_TELEGRAM_CHAT_ID found in docs/ARCHITECTURE.md" in wrong_name_errors(w)
    assert_only_guard_fails(w, "wrong_names", guards=GUARDS)


def test_guard3_covers_deployments(world):
    rel = "deployments/all-in-one/README.md"
    assert rel in world["files"]
    files = {**world["files"], rel: world["files"][rel] + "\nVPN_SENTINEL_TELEGRAM_BOT_TOKEN=1\n"}
    assert_only_guard_fails({**world, "files": files}, "wrong_names", guards=GUARDS)
