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


def test_verify_is_a_known_command():
    # With no Docker available in unit context, verify should fail LOUDLY,
    # not print "Unknown command".
    res = run("verify", "--dry-run")
    assert "Unknown command" not in (res.stdout + res.stderr)
