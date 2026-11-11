"""Unit tests for the Prometheus /metrics endpoint (metrics.py, client_health.py)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from prometheus_client.exposition import CONTENT_TYPE_PLAIN_0_0_4
from prometheus_client.parser import text_string_to_metric_families

from vpn_sentinel.common import api_routes, metrics
from vpn_sentinel.common.api_routes import _run_cleanup_sweep, client_status, client_status_lock
from vpn_sentinel.common.client_health import classify_client
from vpn_sentinel.common.health_routes import health_app

SERVER_IP = "198.51.100.5"
TS_KEY = "vpn_sentinel_client_last_keepalive_timestamp_seconds"


def _iso(minutes_ago=0):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


def _client(**over):
    base = {
        "last_seen": _iso(),
        "ip": "203.0.113.7",
        "country": "FR",
        "dns_loc": "FR",
        "city": "Paris",
        "region": "Ile-de-France",
        "location": "Paris, Ile-de-France, FR",
    }
    base.update(over)
    return base


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    client_status.clear()
    monkeypatch.setattr(api_routes, "_server_public_ip", SERVER_IP)
    monkeypatch.delenv("VPN_SENTINEL_METRICS_ENABLED", raising=False)
    monkeypatch.setattr(metrics, "METRICS_TOKEN", "")
    metrics.reset_auth_failure_throttle()
    yield
    client_status.clear()


@pytest.fixture
def http():
    health_app.config["TESTING"] = True
    with health_app.test_client() as c:
        yield c


def _samples(body):
    out = {}
    for fam in text_string_to_metric_families(body):
        for s in fam.samples:
            out[(s.name, tuple(sorted(s.labels.items())))] = s.value
    return out


def _get(http):
    resp = http.get("/metrics")
    return resp, resp.get_data(as_text=True)


class TestClassifyClient:
    def test_green(self):
        assert classify_client(_client(), SERVER_IP) == "green"

    def test_yellow_dns_leak(self):
        assert classify_client(_client(dns_loc="US"), SERVER_IP) == "yellow"

    def test_yellow_dns_undetectable(self):
        assert classify_client(_client(dns_loc="Unknown"), SERVER_IP) == "yellow"

    def test_red_same_ip(self):
        assert classify_client(_client(ip=SERVER_IP), SERVER_IP) == "red"

    @pytest.mark.parametrize("ip", ["unknown", "Unknown"])
    def test_red_undetectable_ip(self, ip):
        assert classify_client(_client(ip=ip), SERVER_IP) == "red"


class TestExposition:
    def test_content_type_and_parsable(self, http):
        client_status["a-green"] = _client()
        resp, body = _get(http)
        assert resp.status_code == 200
        assert resp.headers["Content-Type"] == CONTENT_TYPE_PLAIN_0_0_4
        assert list(text_string_to_metric_families(body))

    def test_two_clients_green_and_red(self, http):
        client_status["a-green"] = _client()
        client_status["b-red"] = _client(ip=SERVER_IP)
        _, body = _get(http)
        s = _samples(body)
        assert s[("vpn_sentinel_clients", (("status", "green"),))] == 1.0
        assert s[("vpn_sentinel_clients", (("status", "red"),))] == 1.0
        assert s[("vpn_sentinel_clients", (("status", "yellow"),))] == 0.0
        assert s[("vpn_sentinel_server_ip_known", ())] == 1.0
        assert s[("vpn_sentinel_up", ())] == 1.0

    def test_status_mapping_per_client(self, http):
        client_status["g"] = _client()
        client_status["y"] = _client(dns_loc="US")
        client_status["r"] = _client(ip=SERVER_IP)
        _, body = _get(http)
        s = _samples(body)
        assert s[("vpn_sentinel_client_status", (("client_id", "g"),))] == 0.0
        assert s[("vpn_sentinel_client_status", (("client_id", "y"),))] == 1.0
        assert s[("vpn_sentinel_client_status", (("client_id", "r"),))] == 2.0

    def test_last_keepalive_timestamp(self, http):
        ts = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        client_status["a"] = _client(last_seen=ts.isoformat())
        _, body = _get(http)
        assert _samples(body)[(TS_KEY, (("client_id", "a"),))] == ts.timestamp()

    def test_naive_last_seen_treated_as_utc(self, http):
        client_status["a"] = _client(last_seen="2026-01-02T03:04:05")
        _, body = _get(http)
        expected = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc).timestamp()
        assert _samples(body)[(TS_KEY, (("client_id", "a"),))] == expected

    def test_zero_clients_gauges_present(self, http):
        _, body = _get(http)
        s = _samples(body)
        for status in ("green", "yellow", "red"):
            assert s[("vpn_sentinel_clients", (("status", status),))] == 0.0

    def test_unparseable_last_seen_has_no_timestamp_sample(self, http):
        client_status["bad"] = _client(last_seen="not-a-date")
        resp, body = _get(http)
        assert resp.status_code == 200
        s = _samples(body)
        assert (TS_KEY, (("client_id", "bad"),)) not in s
        assert ("vpn_sentinel_client_status", (("client_id", "bad"),)) in s

    def test_missing_last_seen_has_no_timestamp_sample(self, http):
        client_status["nolast"] = {"ip": "203.0.113.7"}
        resp, body = _get(http)
        assert resp.status_code == 200
        assert (TS_KEY, (("client_id", "nolast"),)) not in _samples(body)


class TestDataExposure:
    def test_ip_and_geolocation_absent(self, http):
        client_status["a"] = _client()
        # Guard against a vacuous test: the stored key is `ip`, never `public_ip`.
        assert "ip" in client_status["a"] and "public_ip" not in client_status["a"]
        _, body = _get(http)
        for secret in ("203.0.113.7", "Paris", "Ile-de-France", "Paris, Ile-de-France, FR"):
            assert secret not in body
        labels = {k for (_, labels) in _samples(body) for (k, _) in labels}
        assert labels <= {"client_id", "status"}


class TestUnknownServerIp:
    @pytest.mark.parametrize("cached", ["Unknown", None, "", "not-an-ip"])
    def test_no_status_samples_and_no_lookup(self, http, monkeypatch, cached):
        monkeypatch.setattr(api_routes, "_server_public_ip", cached)
        client_status["a"] = _client(ip=SERVER_IP)
        with patch("vpn_sentinel.common.api_routes.get_server_public_ip") as lookup:
            resp, body = _get(http)
        lookup.assert_not_called()
        assert resp.status_code == 200
        s = _samples(body)
        assert not [k for k in s if k[0] == "vpn_sentinel_client_status"]
        assert s[("vpn_sentinel_server_ip_known", ())] == 0.0
        for status in ("green", "yellow", "red"):
            assert s[("vpn_sentinel_clients", (("status", status),))] == 0.0
        # the keepalive timestamp does not depend on the server IP
        assert (TS_KEY, (("client_id", "a"),)) in s

    def test_ipv6_server_ip_is_known(self, http, monkeypatch):
        monkeypatch.setattr(api_routes, "_server_public_ip", "2001:db8::1")
        _, body = _get(http)
        assert _samples(body)[("vpn_sentinel_server_ip_known", ())] == 1.0

    def test_peek_never_fetches(self, monkeypatch):
        monkeypatch.setattr(api_routes, "_server_public_ip", None)
        with patch("vpn_sentinel.common.api_routes.get_server_public_ip") as lookup:
            assert api_routes.peek_cached_server_ip() is None
        lookup.assert_not_called()


class TestToggle:
    def test_enabled_by_default(self, http):
        assert http.get("/metrics").status_code == 200

    @pytest.mark.parametrize("value", ["false", "False", "0", "no", "off"])
    def test_disabled_is_404(self, http, monkeypatch, value):
        monkeypatch.setenv("VPN_SENTINEL_METRICS_ENABLED", value)
        assert http.get("/metrics").status_code == 404

    def test_toggle_read_per_request(self, http, monkeypatch):
        monkeypatch.setenv("VPN_SENTINEL_METRICS_ENABLED", "false")
        assert http.get("/metrics").status_code == 404
        monkeypatch.setenv("VPN_SENTINEL_METRICS_ENABLED", "true")
        assert http.get("/metrics").status_code == 200

    def test_post_is_405(self, http):
        assert http.post("/metrics").status_code == 405


class TestLocking:
    def test_lock_released_before_families_are_built(self):
        client_status["a"] = _client()
        held_during_build = []
        real_build = metrics._build_families

        def spy(snapshot, server_ip):
            held_during_build.append(client_status_lock.locked())
            return real_build(snapshot, server_ip)

        with patch.object(metrics, "_build_families", side_effect=spy):
            metrics.render_metrics()
        assert held_during_build == [False]

    def test_registry_is_private_and_rebuildable(self):
        assert metrics.build_registry() is not metrics.build_registry()


class TestEviction:
    @patch("vpn_sentinel.common.api_routes.telegram")
    def test_evicted_client_series_disappear(self, _tg, http):
        client_status["stale"] = _client(last_seen=_iso(120))
        client_status["fresh"] = _client()
        _run_cleanup_sweep()
        _, body = _get(http)
        assert 'client_id="stale"' not in body
        assert 'client_id="fresh"' in body


REALM = 'Bearer realm="vpn-sentinel-metrics"'


class TestMetricsToken:
    @pytest.fixture(autouse=True)
    def token(self, monkeypatch):
        monkeypatch.setattr(metrics, "METRICS_TOKEN", "abc")

    def test_no_token_configured_serves_without_header(self, http, monkeypatch):
        monkeypatch.setattr(metrics, "METRICS_TOKEN", "")
        resp, body = _get(http)
        assert resp.status_code == 200
        assert "vpn_sentinel_clients" in body

    @pytest.mark.parametrize("header", ["Bearer abc", "bearer abc", "BEARER abc"])
    def test_right_token_is_served(self, http, header):
        resp = http.get("/metrics", headers={"Authorization": header})
        assert resp.status_code == 200
        assert "vpn_sentinel_clients" in resp.get_data(as_text=True)

    @pytest.mark.parametrize(
        "headers",
        [
            {},
            {"Authorization": "Bearer abd"},
            {"Authorization": "Basic abc"},
            {"Authorization": "Bearer"},
            {"Authorization": "Bearer "},
            {"Authorization": "Bearer " + "x" * 20000},
        ],
    )
    def test_everything_else_is_401(self, http, headers):
        resp = http.get("/metrics", headers=headers)
        assert resp.status_code == 401
        assert resp.headers["WWW-Authenticate"] == REALM
        assert resp.headers["Cache-Control"] == "no-store"
        body = resp.get_data(as_text=True)
        assert body == "Unauthorized"
        assert "vpn_sentinel" not in body

    def test_disabled_wins_over_token(self, http, monkeypatch):
        monkeypatch.setenv("VPN_SENTINEL_METRICS_ENABLED", "false")
        resp = http.get("/metrics", headers={"Authorization": "Bearer abc"})
        assert resp.status_code == 404

    def test_health_stays_public(self, http):
        assert http.get("/health").status_code == 200

    def test_compare_is_constant_time(self, http):
        with patch("vpn_sentinel.common.health_routes.hmac.compare_digest", return_value=True) as cmp:
            resp = http.get("/metrics", headers={"Authorization": "Bearer whatever"})
        assert cmp.called
        assert resp.status_code == 200


class TestMetricsAuthFailureLog:
    @pytest.fixture(autouse=True)
    def token(self, monkeypatch):
        monkeypatch.setattr(metrics, "METRICS_TOKEN", "S3NT1NEL")

    def test_five_failures_log_one_line_then_summary_after_window(self, http, capsys, monkeypatch):
        clock = [1000.0]
        monkeypatch.setattr(metrics.time, "monotonic", lambda: clock[0])
        capsys.readouterr()
        for _ in range(5):
            assert http.get("/metrics", headers={"Authorization": "Bearer wrong"}).status_code == 401
        out = capsys.readouterr().out
        assert out.count("metrics auth failed") == 1
        assert "S3NT1NEL" not in out and "wrong" not in out

        clock[0] += 61
        http.get("/metrics", headers={"Authorization": "Bearer wrong"})
        out = capsys.readouterr().out
        assert out.count("metrics auth failed") == 1
        assert "(4 more suppressed)" in out
        assert "S3NT1NEL" not in out

    def test_logged_ip_is_remote_addr_not_forwarded_for(self, http, capsys):
        capsys.readouterr()
        http.get(
            "/metrics",
            headers={"X-Forwarded-For": "1.2.3.4"},
            environ_overrides={"REMOTE_ADDR": "198.51.100.77"},
        )
        out = capsys.readouterr().out
        assert "IP: 198.51.100.77" in out
        assert "1.2.3.4" not in out
