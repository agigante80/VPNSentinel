"""Genuine end-to-end test against the live local Docker stack.

Runs only when VPN_SENTINEL_E2E=1 (set by `bin/local-env verify`). When the flag is
set, the stack is expected to be UP: connection failures are hard errors, never skips.
Brought up by tests/docker-compose.test.yaml (see bin/local-env).
"""
import json
import os
import time

import pytest
import requests

E2E_ENABLED = os.getenv("VPN_SENTINEL_E2E") == "1"

HOST = os.getenv("VPN_SENTINEL_SERVER_HOST", "localhost")
API_PORT = os.getenv("VPN_SENTINEL_E2E_API_PORT", "15554")
HEALTH_PORT = os.getenv("VPN_SENTINEL_E2E_HEALTH_PORT", "15553")
DASH_PORT = os.getenv("VPN_SENTINEL_E2E_DASHBOARD_PORT", "18080")
API_PATH = os.getenv("VPN_SENTINEL_API_PATH", "/test/v1")
API_KEY = os.getenv("VPN_SENTINEL_API_KEY", "test-api-key-abcdef123456789")

API = f"http://{HOST}:{API_PORT}{API_PATH}"
HEALTH_URL = f"http://{HOST}:{HEALTH_PORT}/health"
DASHBOARD_URL = f"http://{HOST}:{DASH_PORT}/dashboard"
AUTH = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

pytestmark = pytest.mark.skipif(
    not E2E_ENABLED,
    reason="Set VPN_SENTINEL_E2E=1 (via `bin/local-env verify`) to run live-stack E2E.",
)


def _payload(client_id):
    return {
        "client_id": client_id,
        "timestamp": "2026-06-21T00:00:00+00:00",
        "public_ip": "203.0.113.10",
        "status": "alive",
        "location": {"country": "US", "city": "X", "region": "Y",
                     "org": "AS1 Z", "timezone": "UTC"},
        "dns_test": {"location": "US", "colo": "NYC"},
    }


def test_server_health_ok():
    resp = requests.get(HEALTH_URL, timeout=10)
    assert resp.status_code == 200, f"health {HEALTH_URL} -> {resp.status_code}"


def test_keepalive_then_status_shows_client():
    client_id = f"e2e-probe-{int(time.time())}"
    ka = requests.post(f"{API}/keepalive", headers=AUTH,
                       data=json.dumps(_payload(client_id)), timeout=10)
    assert ka.status_code == 200, f"keepalive -> {ka.status_code}: {ka.text}"
    assert ka.json().get("status") == "ok"

    status = requests.get(f"{API}/status", headers=AUTH, timeout=10)
    assert status.status_code == 200
    data = status.json()
    assert client_id in data, f"{client_id} not in /status keys: {list(data)}"
    assert "last_seen" in data[client_id], f"expected last_seen in record: {data[client_id]}"


def test_compose_client_registers_real_keepalive():
    # The compose vpn-sentinel-client-test container posts on its own interval.
    deadline = time.time() + 60
    seen = []
    while time.time() < deadline:
        resp = requests.get(f"{API}/status", headers=AUTH, timeout=10)
        if resp.status_code == 200:
            seen = list(resp.json().keys())
            if "test-client-docker" in seen:
                break
        time.sleep(2)
    assert "test-client-docker" in seen, f"compose client never registered; saw {seen}"


def test_dashboard_reachable():
    resp = requests.get(DASHBOARD_URL, timeout=10)
    assert resp.status_code == 200
