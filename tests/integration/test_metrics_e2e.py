"""Live-stack E2E for the Prometheus /metrics endpoint on the health app.

Runs only when VPN_SENTINEL_E2E=1 (set by `bin/local-env verify`). The stack is expected to be UP.
/metrics requires a bearer token on the test stack: it is read from VPN_SENTINEL_E2E_METRICS_TOKEN (set it when
running against a stack with a non-default token) and defaults to the value in tests/.env.test, like API_KEY.
The unique basename matters: tests/unit/test_metrics.py exists and neither folder has an __init__.py.
"""

import json
import os
import re
import time

import pytest
import requests
from prometheus_client.exposition import CONTENT_TYPE_PLAIN_0_0_4
from prometheus_client.parser import text_string_to_metric_families

E2E_ENABLED = os.getenv("VPN_SENTINEL_E2E") == "1"

HOST = os.getenv("VPN_SENTINEL_SERVER_HOST", "localhost")
API_PORT = os.getenv("VPN_SENTINEL_E2E_API_PORT", "15554")
HEALTH_PORT = os.getenv("VPN_SENTINEL_E2E_HEALTH_PORT", "15553")
API_PATH = os.getenv("VPN_SENTINEL_API_PATH", "/test/v1")
API_KEY = os.getenv("VPN_SENTINEL_API_KEY", "test-api-key-abcdef123456789")

METRICS_TOKEN = os.getenv("VPN_SENTINEL_E2E_METRICS_TOKEN", "test-metrics-token-0123456789")

API = f"http://{HOST}:{API_PORT}{API_PATH}"
METRICS_URL = f"http://{HOST}:{HEALTH_PORT}/metrics"
METRICS_AUTH = {"Authorization": f"Bearer {METRICS_TOKEN}"}
AUTH = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
CLIENT_IP = "203.0.113.10"

pytestmark = pytest.mark.skipif(
    not E2E_ENABLED,
    reason="Set VPN_SENTINEL_E2E=1 (via `bin/local-env verify`) to run live-stack E2E.",
)


def _payload(client_id):
    return {
        "client_id": client_id,
        "timestamp": "2026-06-21T00:00:00+00:00",
        "public_ip": CLIENT_IP,
        "status": "alive",
        "location": {"country": "US", "city": "X", "region": "Y", "org": "AS1 Z", "timezone": "UTC"},
        "dns_test": {"location": "US", "colo": "NYC"},
    }


def _samples(body):
    out = {}
    for fam in text_string_to_metric_families(body):
        for s in fam.samples:
            out[(s.name, tuple(sorted(s.labels.items())))] = s.value
    return out


def _send_keepalive(client_id):
    ka = requests.post(f"{API}/keepalive", headers=AUTH, data=json.dumps(_payload(client_id)), timeout=30)
    assert ka.status_code == 200, f"keepalive -> {ka.status_code}: {ka.text}"


def test_metrics_happy_path():
    client_id = f"e2e-metrics-{int(time.time())}"
    _send_keepalive(client_id)

    resp = requests.get(METRICS_URL, headers=METRICS_AUTH, timeout=10)
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == CONTENT_TYPE_PLAIN_0_0_4

    s = _samples(resp.text)
    assert s[("vpn_sentinel_up", ())] == 1.0
    assert ("vpn_sentinel_client_last_keepalive_timestamp_seconds", (("client_id", client_id),)) in s
    assert ("vpn_sentinel_server_ip_known", ()) in s

    # The status sample exists only when the server IP lookup succeeded; do not fail offline hosts.
    status_key = ("vpn_sentinel_client_status", (("client_id", client_id),))
    if s[("vpn_sentinel_server_ip_known", ())] == 1.0:
        assert s[status_key] in (0.0, 1.0, 2.0)
    else:
        assert status_key not in s


def test_metrics_unhappy_path():
    client_id = f"e2e-metrics-neg-{int(time.time())}"
    _send_keepalive(client_id)

    assert requests.post(METRICS_URL, timeout=10).status_code == 405

    body = requests.get(METRICS_URL, headers=METRICS_AUTH, timeout=10).text
    assert CLIENT_IP not in body
    assert not re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", body)


def test_metrics_requires_the_token():
    resp = requests.get(METRICS_URL, timeout=10)
    assert resp.status_code == 401
    assert resp.headers["WWW-Authenticate"] == 'Bearer realm="vpn-sentinel-metrics"'


def test_metrics_wrong_token_is_401_without_metric_names():
    resp = requests.get(METRICS_URL, headers={"Authorization": "Bearer wrong-" + METRICS_TOKEN}, timeout=10)
    assert resp.status_code == 401
    assert "vpn_sentinel" not in resp.text
