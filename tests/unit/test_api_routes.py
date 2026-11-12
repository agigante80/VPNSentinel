"""
Unit tests for API routes (api_routes.py)
Tests keepalive endpoint, status endpoint, client registration, and data parsing.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from vpn_sentinel.common import api_routes, security
from vpn_sentinel.common.api_routes import api_app, client_status, _client_first_seen, get_cached_server_ip


@pytest.fixture
def client():
    """Create Flask test client."""
    api_app.config["TESTING"] = True
    with api_app.test_client() as client:
        yield client


@pytest.fixture
def clear_client_data():
    """Clear client data before each test."""
    client_status.clear()
    _client_first_seen.clear()
    yield
    client_status.clear()
    _client_first_seen.clear()


class TestGetStatus:
    """Tests for GET /status endpoint."""

    def test_get_status_empty(self, client, clear_client_data):
        """Test status endpoint returns empty dict when no clients."""
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        assert response.json == {}

    def test_get_status_with_clients(self, client, clear_client_data):
        """Test status endpoint returns client data."""
        # Add test data
        client_status["test-client"] = {
            "ip": "1.2.3.4",
            "location": "London, England, GB",
            "last_seen": "2025-11-11T10:00:00",
        }

        response = client.get("/api/v1/status")
        assert response.status_code == 200
        assert "test-client" in response.json
        assert response.json["test-client"]["ip"] == "1.2.3.4"


class TestKeepalive:
    """Tests for POST /keepalive endpoint."""

    @patch("vpn_sentinel.common.api_routes.get_cached_server_ip")
    @patch("vpn_sentinel.common.api_routes.telegram")
    @patch("vpn_sentinel.common.api_routes.log_info")
    def test_keepalive_flat_format_success(self, mock_log, mock_telegram, mock_server_ip, client, clear_client_data):
        """Test keepalive with flat JSON format."""
        mock_server_ip.return_value = "79.116.8.43"

        payload = {
            "client_id": "test-client",
            "public_ip": "91.203.5.146",
            "city": "London",
            "region": "England",
            "country": "GB",
            "provider": "M247 Ltd",
            "timezone": "Europe/London",
            "dns_loc": "GB",
            "dns_colo": "LHR",
        }

        response = client.post("/api/v1/keepalive", json=payload)

        assert response.status_code == 200
        assert response.json["status"] == "ok"
        assert "server_time" in response.json

        # Verify client data stored
        assert "test-client" in client_status
        assert client_status["test-client"]["ip"] == "91.203.5.146"
        assert client_status["test-client"]["city"] == "London"
        assert client_status["test-client"]["country"] == "GB"
        assert client_status["test-client"]["dns_loc"] == "GB"

        # Verify Telegram notification sent for new client
        mock_telegram.notify_client_connected.assert_called_once()

    @patch("vpn_sentinel.common.api_routes.get_cached_server_ip")
    @patch("vpn_sentinel.common.api_routes.telegram")
    @patch("vpn_sentinel.common.api_routes.log_info")
    def test_keepalive_nested_format_success(self, mock_log, mock_telegram, mock_server_ip, client, clear_client_data):
        """Test keepalive with nested JSON format."""
        mock_server_ip.return_value = "79.116.8.43"

        payload = {
            "client_id": "test-client",
            "public_ip": "91.203.5.146",
            "location": {
                "city": "London",
                "region": "England",
                "country": "GB",
                "org": "M247 Ltd",
                "timezone": "Europe/London",
            },
            "dns_test": {"location": "GB", "colo": "LHR"},
        }

        response = client.post("/api/v1/keepalive", json=payload)

        assert response.status_code == 200
        assert response.json["status"] == "ok"

        # Verify client data stored
        assert "test-client" in client_status
        assert client_status["test-client"]["country"] == "GB"
        assert client_status["test-client"]["dns_loc"] == "GB"

    def test_keepalive_missing_json(self, client, clear_client_data):
        """Test keepalive fails without JSON data."""
        response = client.post("/api/v1/keepalive", headers={"Content-Type": "application/json"}, data="")
        # Flask returns 500 when get_json fails, but our try/except catches it
        assert response.status_code in [400, 500]
        assert "error" in response.json

    def test_keepalive_missing_client_id(self, client, clear_client_data):
        """Test keepalive fails without client_id."""
        payload = {"public_ip": "1.2.3.4"}
        response = client.post("/api/v1/keepalive", json=payload)
        assert response.status_code == 400
        assert "error" in response.json
        assert "client_id is required" in response.json["error"]

    @patch("vpn_sentinel.common.api_routes.get_cached_server_ip")
    @patch("vpn_sentinel.common.api_routes.telegram")
    @patch("vpn_sentinel.common.api_routes.log_info")
    @patch("vpn_sentinel.common.api_routes.log_warn")
    def test_keepalive_vpn_bypass_detection(
        self, mock_log_warn, mock_log, mock_telegram, mock_server_ip, client, clear_client_data
    ):
        """Test VPN bypass detection when client IP matches server IP."""
        server_ip = "79.116.8.43"
        mock_server_ip.return_value = server_ip

        payload = {
            "client_id": "bypass-client",
            "public_ip": server_ip,  # Same as server!
            "city": "Madrid",
            "region": "Madrid",
            "country": "ES",
            "provider": "Hetzner",
            "dns_loc": "ES",
        }

        response = client.post("/api/v1/keepalive", json=payload)

        assert response.status_code == 200
        # Verify warning was logged
        mock_log_warn.assert_called()
        args = mock_log_warn.call_args[0]
        assert "security" in args
        assert "VPN BYPASS WARNING" in args[1]

    @patch("vpn_sentinel.common.api_routes.get_cached_server_ip")
    @patch("vpn_sentinel.common.api_routes.telegram")
    @patch("vpn_sentinel.common.api_routes.log_info")
    def test_keepalive_ip_change_notification(self, mock_log, mock_telegram, mock_server_ip, client, clear_client_data):
        """Test IP change notification when client IP changes."""
        mock_server_ip.return_value = "79.116.8.43"

        # First keepalive
        payload1 = {
            "client_id": "test-client",
            "public_ip": "1.2.3.4",
            "city": "London",
            "country": "GB",
            "dns_loc": "GB",
        }
        client.post("/api/v1/keepalive", json=payload1)

        # Second keepalive with different IP
        payload2 = {
            "client_id": "test-client",
            "public_ip": "5.6.7.8",  # Changed!
            "city": "Paris",
            "country": "FR",
            "dns_loc": "FR",
        }
        response = client.post("/api/v1/keepalive", json=payload2)

        assert response.status_code == 200

        # Verify IP change notification sent
        mock_telegram.notify_ip_changed.assert_called_once()
        args = mock_telegram.notify_ip_changed.call_args[0]
        assert args[0] == "test-client"
        assert args[1] == "1.2.3.4"  # Old IP
        assert args[2] == "5.6.7.8"  # New IP

    @patch("vpn_sentinel.common.api_routes.get_cached_server_ip")
    @patch("vpn_sentinel.common.api_routes.telegram")
    @patch("vpn_sentinel.common.api_routes.log_info")
    def test_keepalive_defaults_for_missing_fields(
        self, mock_log, mock_telegram, mock_server_ip, client, clear_client_data
    ):
        """Test keepalive uses defaults for missing optional fields."""
        mock_server_ip.return_value = "79.116.8.43"

        payload = {
            "client_id": "minimal-client",
            "public_ip": "1.2.3.4",
            # Missing: city, region, country, provider, timezone, dns_loc
        }

        response = client.post("/api/v1/keepalive", json=payload)

        assert response.status_code == 200

        # Verify defaults applied
        assert client_status["minimal-client"]["city"] == "unknown"
        assert client_status["minimal-client"]["country"] == "unknown"
        assert client_status["minimal-client"]["dns_loc"] == "Unknown"

    @patch("vpn_sentinel.common.api_routes.get_cached_server_ip")
    @patch("vpn_sentinel.common.api_routes.telegram")
    @patch("vpn_sentinel.common.api_routes.log_info")
    def test_keepalive_handles_ip_field_fallback(
        self, mock_log, mock_telegram, mock_server_ip, client, clear_client_data
    ):
        """Test keepalive falls back to 'ip' field if 'public_ip' not present."""
        mock_server_ip.return_value = "79.116.8.43"

        payload = {"client_id": "test-client", "ip": "1.2.3.4", "country": "GB"}  # Using 'ip' instead of 'public_ip'

        response = client.post("/api/v1/keepalive", json=payload)

        assert response.status_code == 200
        assert client_status["test-client"]["ip"] == "1.2.3.4"

    @patch("vpn_sentinel.common.api_routes.client_status")
    @patch("vpn_sentinel.common.api_routes.get_cached_server_ip")
    @patch("vpn_sentinel.common.api_routes.log_info")
    def test_keepalive_exception_handling(
        self, mock_log, mock_server_ip, mock_client_status, client, clear_client_data
    ):
        """Test keepalive handles exceptions gracefully."""
        # Mock client_status to raise exception during update
        mock_server_ip.return_value = "79.116.8.43"
        mock_client_status.__setitem__.side_effect = Exception("Test error")

        response = client.post("/api/v1/keepalive", json={"client_id": "test", "public_ip": "1.2.3.4"})

        # Should return 500 for internal errors
        assert response.status_code == 500
        assert "error" in response.json


class TestGetCachedServerIp:
    """Tests for get_cached_server_ip function."""

    @patch("vpn_sentinel.common.api_routes.get_server_public_ip")
    def test_caches_server_ip(self, mock_get_ip):
        """Test server IP is cached after first call."""
        mock_get_ip.return_value = "79.116.8.43"

        # Reset cache
        import vpn_sentinel.common.api_routes as api_routes

        api_routes._server_public_ip = None

        # First call should fetch
        ip1 = get_cached_server_ip()
        assert ip1 == "79.116.8.43"
        assert mock_get_ip.call_count == 1

        # Second call should use cache
        ip2 = get_cached_server_ip()
        assert ip2 == "79.116.8.43"
        assert mock_get_ip.call_count == 1  # Not called again


class TestApiPath:
    """Tests for API_PATH configuration."""

    def test_api_path_from_environment(self):
        """Test API_PATH is read from environment."""
        from vpn_sentinel.common.api_routes import API_PATH

        # Should be /api/v1 or custom from VPN_SENTINEL_API_PATH env var
        assert API_PATH.startswith("/")
        assert len(API_PATH) > 1


class TestKeepaliveWithApprise:
    """Apprise targets never delay or reach the keepalive path wrongly (#142)."""

    PAYLOAD = {
        "client_id": "test-client",
        "public_ip": "91.203.5.146",
        "city": "London",
        "region": "England",
        "country": "GB",
        "provider": "M247 Ltd",
        "timezone": "Europe/London",
        "dns_loc": "GB",
        "dns_colo": "LHR",
    }

    @patch("vpn_sentinel.common.api_routes.get_cached_server_ip", return_value="79.116.8.43")
    def test_blackholed_target_does_not_delay_a_new_client_keepalive(
        self, _server_ip, client, clear_client_data, monkeypatch
    ):
        import threading
        import time
        from vpn_sentinel.common import notifications, telegram

        release = threading.Event()
        started = threading.Event()

        def blackhole(targets, title, body):
            started.set()
            release.wait(30)
            return None

        monkeypatch.setenv("VPN_SENTINEL_APPRISE_URLS", "json://blackhole.invalid/x")
        try:
            with (
                patch.object(telegram, "TELEGRAM_ENABLED", False),
                patch.object(notifications, "_apprise_send", side_effect=blackhole),
            ):
                begin = time.monotonic()
                response = client.post("/api/v1/keepalive", json=self.PAYLOAD)
                elapsed = time.monotonic() - begin
                assert response.status_code == 200
                assert elapsed < 2.0
                assert started.wait(5)
        finally:
            release.set()

    @patch("vpn_sentinel.common.api_routes.get_cached_server_ip", return_value="79.116.8.43")
    def test_hostile_client_id_is_rejected_before_any_apprise_call(
        self, _server_ip, client, clear_client_data, monkeypatch
    ):
        from vpn_sentinel.common import notifications

        monkeypatch.setenv("VPN_SENTINEL_APPRISE_URLS", "json://h/x")
        with patch.object(notifications, "_apprise_send") as send:
            response = client.post("/api/v1/keepalive", json=dict(self.PAYLOAD, client_id="<script>"))
            assert notifications.flush() is True
        assert response.status_code == 400
        assert "Invalid client_id format" in response.get_data(as_text=True)
        send.assert_not_called()

    @patch("vpn_sentinel.common.api_routes.get_cached_server_ip", return_value="79.116.8.43")
    def test_new_client_alert_is_sent_outside_client_status_lock(self, _server_ip, client, clear_client_data):
        from vpn_sentinel.common import api_routes, notifications

        seen = []

        def fake_notify(title, body):
            free = api_routes.client_status_lock.acquire(blocking=False)
            if free:
                api_routes.client_status_lock.release()
            seen.append(free)
            return True

        with patch.object(notifications, "notify", side_effect=fake_notify):
            assert client.post("/api/v1/keepalive", json=self.PAYLOAD).status_code == 200
        assert seen == [True]


class TestApiKeyMiddleware:
    """authenticate_request: 401 missing key, 403 wrong key, 200 right key, auth disabled when no key."""

    KEY = "k1"
    PAYLOAD = {"client_id": "auth-client", "public_ip": "91.203.5.146"}

    @pytest.fixture(autouse=True)
    def isolate(self, monkeypatch, clear_client_data):
        """Fresh rate-limit store so these tests can neither cause nor suffer a 429."""
        security.rate_limit_storage.clear()
        monkeypatch.setattr(api_routes, "API_KEY", self.KEY)
        yield
        security.rate_limit_storage.clear()

    def _post(self, client, headers=None):
        with (
            patch("vpn_sentinel.common.api_routes.get_cached_server_ip", return_value="79.116.8.43"),
            patch("vpn_sentinel.common.api_routes.telegram"),
        ):
            return client.post("/api/v1/keepalive", json=self.PAYLOAD, headers=headers or {})

    def test_right_key_is_authorised(self, client):
        assert self._post(client, {"X-API-Key": "k1"}).status_code == 200

    @pytest.mark.parametrize("bad", ["k2", "k1x", "K1"])
    def test_wrong_key_is_403(self, client, bad):
        resp = self._post(client, {"X-API-Key": bad})
        assert resp.status_code == 403
        assert resp.json == {"error": "Authentication failed", "message": "Invalid API key"}

    def test_missing_key_is_401(self, client):
        resp = self._post(client)
        assert resp.status_code == 401
        assert resp.json == {"error": "Authentication required", "message": "X-API-Key header is required"}

    def test_auth_disabled_when_no_key_configured(self, client, monkeypatch):
        monkeypatch.setattr(api_routes, "API_KEY", "")
        with patch("vpn_sentinel.common.api_routes.secrets_match") as spy:
            assert self._post(client).status_code == 200
        assert not spy.called

    def test_non_ascii_key_from_bundled_client_latin1(self, client, monkeypatch):
        key = "cl\u00e9-secr\u00e8te"
        monkeypatch.setattr(api_routes, "API_KEY", key)
        # Werkzeug hands the app the latin-1 decoded header: for the bundled client that is the key itself.
        assert self._post(client, {"X-API-Key": key}).status_code == 200

    def test_non_ascii_key_from_utf8_client(self, client, monkeypatch):
        key = "cl\u00e9-secr\u00e8te"
        monkeypatch.setattr(api_routes, "API_KEY", key)
        resp = client.post(
            "/api/v1/keepalive",
            json=self.PAYLOAD,
            environ_overrides={"HTTP_X_API_KEY": key.encode("utf-8").decode("latin-1")},
        )
        assert resp.status_code == 200

    def test_non_ascii_near_miss_is_403(self, client, monkeypatch):
        monkeypatch.setattr(api_routes, "API_KEY", "cl\u00e9-secr\u00e8te")
        assert self._post(client, {"X-API-Key": "cle-secrete"}).status_code == 403

    def test_call_site_uses_secrets_match(self, client):
        with patch("vpn_sentinel.common.api_routes.secrets_match", return_value=True) as spy:
            assert self._post(client, {"X-API-Key": "k1"}).status_code == 200
        spy.assert_called_once_with("k1", self.KEY)
