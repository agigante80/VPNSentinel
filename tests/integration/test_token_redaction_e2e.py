"""Live-stack E2E for Telegram bot-token redaction (issue #141).

Runs only when VPN_SENTINEL_E2E=1 (set by `bin/local-env verify`). The two docker compose specs also skip
when docker is not on PATH.
"""

import os
import shutil
import subprocess

import pytest
import requests

E2E_ENABLED = os.getenv("VPN_SENTINEL_E2E") == "1"

HOST = os.getenv("VPN_SENTINEL_SERVER_HOST", "localhost")
DASH_PORT = os.getenv("VPN_SENTINEL_E2E_DASHBOARD_PORT") or os.getenv("VPN_SENTINEL_SERVER_DASHBOARD_PORT", "18080")
LOGS_URL = f"http://{HOST}:{DASH_PORT}/logs"
TESTS_DIR = os.path.join(os.path.dirname(__file__), "..")
COMPOSE = [
    "docker",
    "compose",
    "-f",
    os.path.join(TESTS_DIR, "docker-compose.test.yaml"),
    "--env-file",
    os.path.join(TESTS_DIR, ".env.test"),
]
SERVICE = "vpn-sentinel-server-test"
# Expanded by the container shell, so it follows the server's own setting and default (log_utils.py).
LOG_FILE = '"${VPN_SENTINEL_LOG_FILE:-/tmp/vpn-sentinel-server.log}"'

# Fabricated token in the real Telegram shape; never a live credential.
TOKEN = "123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"
TOKEN_TAIL = "AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"
LEAK_LINE = f"url: /bot{TOKEN}/sendMessage"

pytestmark = pytest.mark.skipif(
    not E2E_ENABLED,
    reason="Set VPN_SENTINEL_E2E=1 (via `bin/local-env verify`) to run live-stack E2E.",
)

needs_docker = pytest.mark.skipif(shutil.which("docker") is None, reason="docker not on PATH")


def _exec(shell_cmd):
    return subprocess.run(
        [*COMPOSE, "exec", "-T", SERVICE, "sh", "-c", shell_cmd], capture_output=True, text=True, timeout=60
    )


def test_logs_page_serves_ordinary_lines_unchanged():
    r = requests.get(LOGS_URL, timeout=10)
    assert r.status_code == 200
    # A known startup line must appear verbatim. Not "no [REDACTED]": a reused stack may hold earlier leaks.
    assert "Starting VPN Sentinel Server" in r.text


@needs_docker
def test_old_leaked_line_is_redacted_on_logs_page():
    # Append in place (same inode) because the running server holds the log file open.
    appended = _exec(f"echo '{LEAK_LINE}' >> {LOG_FILE}")
    assert appended.returncode == 0, appended.stderr
    try:
        r = requests.get(LOGS_URL, timeout=10)
        assert r.status_code == 200
        assert "[REDACTED]" in r.text
        assert TOKEN_TAIL not in r.text
    finally:
        # Remove the line again so a later run on a reused container starts clean.
        _exec(
            f"grep -v '{TOKEN_TAIL}' {LOG_FILE} > /tmp/redaction-e2e.clean; cat /tmp/redaction-e2e.clean > {LOG_FILE}; rm -f /tmp/redaction-e2e.clean"
        )


@needs_docker
def test_real_send_failure_does_not_log_token():
    cmd = [
        *COMPOSE,
        "run",
        "--rm",
        "--no-deps",
        "--entrypoint",
        "python",
        "-e",
        "VPN_SENTINEL_TELEGRAM_ENABLED=true",
        "-e",
        f"TELEGRAM_BOT_TOKEN={TOKEN}",
        "-e",
        "TELEGRAM_CHAT_ID=1",
        "-e",
        "HTTPS_PROXY=http://127.0.0.1:9",
        SERVICE,
        "-c",
        "from vpn_sentinel.common import telegram; telegram.send_telegram_message('x')",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    out = r.stdout + r.stderr
    assert "Error sending message" in out, out
    assert "[REDACTED]" in out, out
    assert TOKEN_TAIL not in out, out
