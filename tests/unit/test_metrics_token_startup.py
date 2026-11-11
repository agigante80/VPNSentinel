"""Subprocess tests: VPN_SENTINEL_METRICS_TOKEN(_FILE) is read once at import and a bad file is fatal (exit 1).

Run in subprocesses because the token is read at import time.
"""

import os
import subprocess
import sys

PYTHON = sys.executable or "python3"
SENTINEL = "S3NT1NEL"
IMPORT = "import vpn_sentinel.common.metrics"


def _run(code, env_extra):
    env = os.environ.copy()
    env.pop("VPN_SENTINEL_METRICS_TOKEN", None)
    env.pop("VPN_SENTINEL_METRICS_TOKEN_FILE", None)
    env.update(env_extra)
    env["PYTHONPATH"] = os.getcwd() + os.pathsep + os.path.join(os.getcwd(), "src")
    return subprocess.run([PYTHON, "-c", code], env=env, capture_output=True, text=True, cwd=os.getcwd(), timeout=60)


def _assert_clean_config_exit(result, needle):
    out = result.stdout + result.stderr
    assert result.returncode == 1, out
    assert "[config]" in out and needle in out
    assert "Traceback" not in out
    assert SENTINEL not in out


def test_token_file_content_becomes_token(tmp_path):
    f = tmp_path / "t"
    f.write_text("abc\n")
    r = _run(
        "from vpn_sentinel.common import metrics; print('TOKEN=' + metrics.METRICS_TOKEN)",
        {"VPN_SENTINEL_METRICS_TOKEN_FILE": str(f)},
    )
    assert r.returncode == 0, r.stderr
    assert "TOKEN=abc" in r.stdout


def test_env_token_is_read():
    r = _run(
        "from vpn_sentinel.common import metrics; print('TOKEN=' + metrics.METRICS_TOKEN)",
        {"VPN_SENTINEL_METRICS_TOKEN": "xyz"},
    )
    assert "TOKEN=xyz" in r.stdout


def test_unset_means_empty_token():
    r = _run("from vpn_sentinel.common import metrics; print('TOKEN=[' + metrics.METRICS_TOKEN + ']')", {})
    assert "TOKEN=[]" in r.stdout


def test_missing_file_exits_1(tmp_path):
    _assert_clean_config_exit(
        _run(IMPORT, {"VPN_SENTINEL_METRICS_TOKEN_FILE": str(tmp_path / "missing")}), "cannot be read"
    )


def test_empty_file_exits_1(tmp_path):
    f = tmp_path / "t"
    f.write_text("\n")
    _assert_clean_config_exit(_run(IMPORT, {"VPN_SENTINEL_METRICS_TOKEN_FILE": str(f)}), "is empty")


def test_both_forms_exit_1(tmp_path):
    f = tmp_path / "t"
    f.write_text(SENTINEL)
    r = _run(IMPORT, {"VPN_SENTINEL_METRICS_TOKEN_FILE": str(f), "VPN_SENTINEL_METRICS_TOKEN": SENTINEL})
    _assert_clean_config_exit(r, "Both VPN_SENTINEL_METRICS_TOKEN and VPN_SENTINEL_METRICS_TOKEN_FILE are set")
