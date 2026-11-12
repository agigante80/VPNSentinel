"""bin/local-env verify-notify and the notification E2E skip (issue #143)."""

import os
import stat
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CLI = os.path.join(REPO, "bin", "local-env")


def run(*args, env=None):
    return subprocess.run([CLI, *args], capture_output=True, text=True, env=env, timeout=60)


def test_help_lists_verify_notify():
    res = run("help")
    assert res.returncode == 0
    assert "verify-notify" in res.stdout


def test_dry_run_names_both_compose_files():
    res = run("verify-notify", "--dry-run")
    assert res.returncode == 0
    assert "docker-compose.test.yaml" in res.stdout
    assert "docker-compose.notify.yaml" in res.stdout


def test_unknown_option_exits_2():
    res = run("verify-notify", "--bogus")
    assert res.returncode == 2
    assert "verify-notify: unknown option --bogus" in res.stderr


def test_start_failure_tears_down_both_compose_files(tmp_path):
    """The server never reports healthy: exit 1 and a down -v --remove-orphans with both files."""
    log = tmp_path / "docker.log"
    stubs = tmp_path / "bin"
    stubs.mkdir()
    # docker records its argv; `inspect` prints nothing and fails, so the server is never healthy.
    (stubs / "docker").write_text(f'#!/bin/sh\necho "$*" >> "{log}"\n[ "$1" = inspect ] && exit 1\nexit 0\n')
    (stubs / "sleep").write_text("#!/bin/sh\nexit 0\n")
    for name in ("docker", "sleep"):
        path = stubs / name
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
    env = dict(os.environ, PATH=f"{stubs}{os.pathsep}{os.environ['PATH']}")
    res = run("verify-notify", env=env)
    assert res.returncode == 1
    assert "stack failed to start" in res.stderr
    down = [line for line in log.read_text().splitlines() if "down -v --remove-orphans" in line]
    assert len(down) == 1
    assert "docker-compose.test.yaml" in down[0]
    assert "docker-compose.notify.yaml" in down[0]


def test_notification_e2e_module_skips_without_flag():
    env = {k: v for k, v in os.environ.items() if k != "VPN_SENTINEL_E2E_NOTIFY"}
    env["VPN_SENTINEL_E2E"] = "1"
    res = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/integration/test_notifications_apprise.py", "-rs", "--no-cov", "-q"],
        cwd=REPO,
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert "Set VPN_SENTINEL_E2E_NOTIFY=1 (via bin/local-env verify-notify)" in res.stdout
    assert "failed" not in res.stdout and "error" not in res.stdout.lower().replace("errors=", "")
