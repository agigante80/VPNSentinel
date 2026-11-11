"""The served icon must ship inside the installed package (issue #134).

The server image is built by `pip install --user .` and ships only /root/.local, so docs/images/
never reaches it. A bare non-.py file under src/ is not included unless pyproject.toml declares it.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
STATIC = REPO_ROOT / "src" / "vpn_sentinel" / "common" / "static"


def _package_data():
    try:
        import tomllib
    except ModuleNotFoundError:  # Python 3.10
        tomllib = pytest.importorskip("tomli")
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    return data["tool"]["setuptools"]["package-data"]


def test_pyproject_declares_static_package_data():
    assert "static/*" in _package_data()["vpn_sentinel.common"]


def test_served_icons_exist_in_source_tree():
    assert (STATIC / "favicon.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert b"<svg" in (STATIC / "favicon.svg").read_bytes()


def test_served_copies_match_masters():
    images = REPO_ROOT / "docs" / "images"
    assert (STATIC / "favicon.png").read_bytes() == (images / "icon-256.png").read_bytes()
    assert (STATIC / "favicon.svg").read_bytes() == (images / "icon.svg").read_bytes()
