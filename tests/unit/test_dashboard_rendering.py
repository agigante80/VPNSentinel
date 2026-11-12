"""Regression tests for how the dashboard pages display dynamic values (issue #146).

Values from clients, server geolocation and the log file must be shown literally (HTML-encoded, never
evaluated), and dashboard responses must carry the security headers with a matching script nonce.
"""

import re
import threading
from unittest.mock import patch

import pytest

from vpn_sentinel.common import dashboard_routes
from vpn_sentinel.common.dashboard_routes import dashboard_app
from vpn_sentinel.common.server import api_app

TEMPLATE_TEXT = "{{7*7}}"
EVIL = "<i>x</i>{{7*7}}"


@pytest.fixture
def client():
    dashboard_app.config["TESTING"] = True
    with dashboard_app.test_client() as c:
        yield c


def _patch_log(monkeypatch, tmp_path, text):
    log = tmp_path / "server.log"
    log.write_text(text)
    monkeypatch.setenv("VPN_SENTINEL_LOG_FILE", str(log))


class TestLogsPage:
    def test_template_syntax_in_log_is_shown_literally(self, client, monkeypatch, tmp_path):
        _patch_log(monkeypatch, tmp_path, "INFO Path: /MARK{{7*7}}MARK\n")
        body = client.get("/logs").get_data(as_text=True)
        assert "MARK{{7*7}}MARK" in body
        assert "MARK49MARK" not in body

    def test_markup_in_log_is_encoded(self, client, monkeypatch, tmp_path):
        _patch_log(monkeypatch, tmp_path, "INFO <b>x</b> <script>alert(1)</script>\n")
        body = client.get("/logs").get_data(as_text=True)
        assert "&lt;b&gt;x&lt;/b&gt;" in body
        assert "&lt;script&gt;" in body
        assert "<b>x</b>" not in body
        # Only the page's own nonce-carrying script tag may exist
        assert len(re.findall(r"<script\b", body)) == 1

    def test_highlighting_script_does_not_write_markup(self, client, monkeypatch, tmp_path):
        _patch_log(monkeypatch, tmp_path, "INFO ok\n")
        body = client.get("/logs").get_data(as_text=True)
        assert "innerHTML" not in body
        assert "createElement('span')" in body


class TestDashboardPage:
    def test_client_and_server_values_are_encoded(self, client):
        entry = {
            "ip": EVIL,
            "location": EVIL,
            "provider": EVIL,
            "client_version": EVIL,
            "dns_loc": EVIL,
            "dns_colo": EVIL,
            "last_seen": EVIL,
        }
        info = {"public_ip": "203.0.113.9", "location": EVIL, "provider": EVIL, "dns_status": EVIL}
        with (
            patch.object(dashboard_routes, "client_status", {EVIL: entry}),
            patch.object(dashboard_routes, "client_status_lock", threading.Lock()),
            patch.object(dashboard_routes, "get_server_info", return_value=info),
        ):
            body = client.get("/dashboard").get_data(as_text=True)
        assert "&lt;i&gt;x&lt;/i&gt;{{7*7}}" in body
        assert "<i>x</i>" not in body
        assert "{{7*7}}" in body
        assert "&lt;/i&gt;49" not in body

    def test_version_is_encoded(self, client):
        with patch.object(dashboard_routes, "get_version", return_value="<u>1</u>"):
            body = client.get("/dashboard").get_data(as_text=True)
        assert "&lt;u&gt;1&lt;/u&gt;" in body
        assert "<u>1</u>" not in body


class TestSecurityHeaders:
    @pytest.mark.parametrize("path", ["/dashboard", "/logs"])
    def test_headers_and_matching_nonce(self, client, path):
        resp = client.get(path)
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["X-Frame-Options"] == "DENY"
        assert resp.headers["Referrer-Policy"] == "no-referrer"
        csp = resp.headers["Content-Security-Policy"]
        for part in ("default-src 'self'", "object-src 'none'", "base-uri 'none'", "frame-ancestors 'none'"):
            assert part in csp
        header_nonce = re.search(r"script-src 'nonce-([^']+)'", csp).group(1)
        page_nonces = re.findall(r'<script nonce="([^"]+)"', resp.get_data(as_text=True))
        assert page_nonces == [header_nonce]

    def test_nonce_differs_per_request(self, client):
        a = client.get("/dashboard").headers["Content-Security-Policy"]
        b = client.get("/dashboard").headers["Content-Security-Policy"]
        assert a != b

    def test_non_page_response_has_no_script_allowance(self, client):
        csp = client.get("/no-such-page").headers["Content-Security-Policy"]
        assert "script-src 'none'" in csp

    def test_api_app_responses_do_not_get_dashboard_headers(self):
        resp = api_app.test_client().get("/no-such-route")
        assert "Content-Security-Policy" not in resp.headers
        assert "X-Frame-Options" not in resp.headers
