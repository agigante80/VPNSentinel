"""Live-stack E2E: request paths that reach the log are displayed literally on /logs (issue #146).

Runs only when VPN_SENTINEL_E2E=1 (set by `bin/local-env verify`).
"""

import os

import pytest
import requests

E2E_ENABLED = os.getenv("VPN_SENTINEL_E2E") == "1"

HOST = os.getenv("VPN_SENTINEL_SERVER_HOST", "localhost")
API_PORT = os.getenv("VPN_SENTINEL_E2E_API_PORT", "15554")
API_PATH = os.getenv("VPN_SENTINEL_API_PATH", "/test/v1")
DASH_PORT = os.getenv("VPN_SENTINEL_E2E_DASHBOARD_PORT") or os.getenv("VPN_SENTINEL_SERVER_DASHBOARD_PORT", "18080")
LOGS_URL = f"http://{HOST}:{DASH_PORT}/logs"
DASHBOARD_URL = f"http://{HOST}:{DASH_PORT}/dashboard"

pytestmark = pytest.mark.skipif(
    not E2E_ENABLED,
    reason="Set VPN_SENTINEL_E2E=1 (via `bin/local-env verify`) to run live-stack E2E.",
)


def test_logged_request_path_is_displayed_literally():
    # %7B / %7D are the URL-encoded braces; the server logs the decoded path.
    requests.get(f"http://{HOST}:{API_PORT}{API_PATH}/MARK%7B%7B7*7%7D%7DMARK", timeout=10)
    r = requests.get(LOGS_URL, timeout=10)
    assert r.status_code == 200
    assert "MARK{{7*7}}MARK" in r.text
    assert "MARK49MARK" not in r.text


@pytest.mark.parametrize("url", [LOGS_URL, DASHBOARD_URL])
def test_dashboard_pages_send_security_headers(url):
    r = requests.get(url, timeout=10)
    assert r.status_code == 200
    assert "script-src 'nonce-" in r.headers["Content-Security-Policy"]
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "no-referrer"
