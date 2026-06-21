import subprocess
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CLI = os.path.join(REPO, "bin", "local-env")


def run(*args):
    return subprocess.run([CLI, *args], capture_output=True, text=True)


def test_help_lists_commands():
    res = run("help")
    assert res.returncode == 0
    for cmd in ("start", "stop", "rebuild", "status", "logs", "verify"):
        assert cmd in res.stdout


def test_unknown_command_errors():
    res = run("bogus")
    assert res.returncode != 0
    assert "Unknown command" in (res.stdout + res.stderr)
