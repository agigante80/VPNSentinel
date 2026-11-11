"""Subprocess tests: a bad *_FILE secret is fatal at startup with one `config` log line, no traceback.

Run in subprocesses because the server reads secrets at import time and re-importing
api_routes in-process would re-register routes on the shared Flask app.
"""

import os
import subprocess
import sys

PYTHON = sys.executable or "python3"
SENTINEL = "S3NT1NEL"
CLIENT_KEEPALIVE_MESSAGES = ("Keepalive sent successfully", "Failed to send keepalive", "Error sending keepalive")


def _run(code, env_extra):
    env = os.environ.copy()
    for k in (
        "VPN_SENTINEL_API_KEY",
        "VPN_SENTINEL_API_KEY_FILE",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_BOT_TOKEN_FILE",
        "TELEGRAM_CHAT_ID",
        "TELEGRAM_CHAT_ID_FILE",
        "VPN_SENTINEL_TELEGRAM_ENABLED",
    ):
        env.pop(k, None)
    env.update(env_extra)
    env["PYTHONPATH"] = os.getcwd() + os.pathsep + os.path.join(os.getcwd(), "src")
    return subprocess.run([PYTHON, "-c", code], env=env, capture_output=True, text=True, cwd=os.getcwd(), timeout=60)


def _assert_clean_config_exit(result, code, needle):
    out = result.stdout + result.stderr
    assert result.returncode == code, out
    assert "[config]" in out and needle in out
    assert "Traceback" not in out
    assert SENTINEL not in out


class TestServerSecretFileStartup:
    def test_missing_key_file_exits_1(self, tmp_path):
        r = _run("import vpn_sentinel.common.api_routes", {"VPN_SENTINEL_API_KEY_FILE": str(tmp_path / "missing")})
        _assert_clean_config_exit(r, 1, "cannot be read")

    def test_empty_key_file_exits_1(self, tmp_path):
        f = tmp_path / "k"
        f.write_text("\n")
        r = _run("import vpn_sentinel.common.api_routes", {"VPN_SENTINEL_API_KEY_FILE": str(f)})
        _assert_clean_config_exit(r, 1, "is empty")

    def test_both_key_forms_exit_1(self, tmp_path):
        f = tmp_path / "k"
        f.write_text(SENTINEL)
        r = _run(
            "import vpn_sentinel.common.api_routes",
            {"VPN_SENTINEL_API_KEY_FILE": str(f), "VPN_SENTINEL_API_KEY": SENTINEL},
        )
        _assert_clean_config_exit(r, 1, "Both VPN_SENTINEL_API_KEY and VPN_SENTINEL_API_KEY_FILE are set")

    def test_key_file_content_becomes_api_key(self, tmp_path):
        f = tmp_path / "k"
        f.write_text("s3cret\n")
        r = _run(
            "from vpn_sentinel.common import api_routes; print('KEY=' + api_routes.API_KEY)",
            {"VPN_SENTINEL_API_KEY_FILE": str(f), "VPN_SENTINEL_API_KEY": ""},
        )
        assert r.returncode == 0, r.stderr
        assert "KEY=s3cret" in r.stdout

    def test_both_telegram_token_forms_exit_1(self, tmp_path):
        f = tmp_path / "t"
        f.write_text(SENTINEL)
        r = _run(
            "import vpn_sentinel.common.telegram",
            {"TELEGRAM_BOT_TOKEN": "abc", "TELEGRAM_BOT_TOKEN_FILE": str(f)},
        )
        _assert_clean_config_exit(r, 1, "Both TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_TOKEN_FILE are set; use one")

    def test_chat_id_directory_exits_1(self, tmp_path):
        r = _run("import vpn_sentinel.common.telegram", {"TELEGRAM_CHAT_ID_FILE": str(tmp_path)})
        _assert_clean_config_exit(r, 1, "cannot be read: Is a directory")

    def test_chat_id_from_file_enables_telegram(self, tmp_path):
        f = tmp_path / "c"
        f.write_text("12345\n")
        r = _run(
            "from vpn_sentinel.common import telegram as t; print(t.TELEGRAM_CHAT_ID, t.TELEGRAM_ENABLED)",
            {"TELEGRAM_CHAT_ID_FILE": str(f), "TELEGRAM_BOT_TOKEN": "tok"},
        )
        assert r.returncode == 0, r.stderr
        assert "12345 True" in r.stdout


class TestClientSecretFileStartup:
    def test_missing_key_file_exits_2_before_any_keepalive(self, tmp_path):
        r = _run(
            "from vpn_sentinel.client.__main__ import main; main()",
            {"VPN_SENTINEL_API_KEY_FILE": str(tmp_path / "missing"), "VPN_SENTINEL_URL": "http://127.0.0.1:9"},
        )
        _assert_clean_config_exit(r, 2, "cannot be read")
        out = r.stdout + r.stderr
        for msg in CLIENT_KEEPALIVE_MESSAGES:
            assert msg not in out
