"""Packaging guards for the optional Apprise dependency (#142).

apprise and its tree (click, markdown, PyYAML, requests-oauthlib) must reach the server image only.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_DOCKERFILE = REPO_ROOT / "src/vpn_sentinel/server/Dockerfile"
CLIENT_DOCKERFILE = REPO_ROOT / "src/vpn_sentinel/client/Dockerfile"
SPEC = "apprise>=2.2,<3"


def _project():
    tomllib = pytest.importorskip("tomllib")
    return tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())["project"]


def _pip_install_lines(path):
    return [ln for ln in path.read_text().splitlines() if re.search(r"\bpip\b.*\binstall\b", ln)]


def test_apprise_is_not_a_base_dependency():
    assert not any("apprise" in dep.lower() for dep in _project()["dependencies"])


def test_notify_extra_pins_apprise_2_series():
    assert _project()["optional-dependencies"]["notify"] == [SPEC]


def test_test_requirements_carry_apprise():
    lines = [ln.strip() for ln in (REPO_ROOT / "tests/requirements.txt").read_text().splitlines()]
    assert SPEC in lines


def test_server_dockerfile_installs_the_notify_extra():
    assert any(".[notify]" in ln for ln in _pip_install_lines(SERVER_DOCKERFILE))


def test_client_dockerfile_never_installs_the_extra_or_apprise():
    lines = _pip_install_lines(CLIENT_DOCKERFILE)
    assert lines, "selector matched no pip install line"
    assert not any("notify" in ln or "apprise" in ln for ln in lines)
    assert "apprise" not in CLIENT_DOCKERFILE.read_text().lower()
