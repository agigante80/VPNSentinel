"""Live Apprise delivery E2E (issue #143).

Runs only via `bin/local-env verify-notify`, which brings up the base test stack plus
tests/docker-compose.notify.yaml (a receiver with a /hook and a /hang target). Gated on
VPN_SENTINEL_E2E_NOTIFY alone, because the CI integration job runs this directory against
the base stack, where there is no receiver.

Assertions match by unique client ID, never by message count: the standing test client is
also evicted in this stack.
"""

import json
import os
import shutil
import subprocess
import time
import uuid

import pytest
import requests

HOST = os.getenv("VPN_SENTINEL_SERVER_HOST", "localhost")
API_PORT = os.getenv("VPN_SENTINEL_E2E_API_PORT", "15554")
API_PATH = os.getenv("VPN_SENTINEL_API_PATH", "/test/v1")
API_KEY = os.getenv("VPN_SENTINEL_API_KEY", "test-api-key-abcdef123456789")

API = f"http://{HOST}:{API_PORT}{API_PATH}"
AUTH = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
RECEIVER = "vpn-sentinel-notify-receiver"
_READ = (
    "import urllib.request;print(urllib.request.urlopen('http://localhost:8099/messages',timeout=5).read().decode())"
)

pytestmark = [
    pytest.mark.skipif(
        os.getenv("VPN_SENTINEL_E2E_NOTIFY") != "1",
        reason="Set VPN_SENTINEL_E2E_NOTIFY=1 (via bin/local-env verify-notify)",
    ),
    pytest.mark.skipif(shutil.which("docker") is None, reason="docker CLI not available"),
]


def _payload(client_id, ip="203.0.113.10"):
    return {
        "client_id": client_id,
        "timestamp": "2026-06-21T00:00:00+00:00",
        "public_ip": ip,
        "status": "alive",
        "location": {"country": "US", "city": "X", "region": "Y", "org": "AS1 Z", "timezone": "UTC"},
        "dns_test": {"location": "US", "colo": "NYC"},
    }


def _keepalive(client_id, ip="203.0.113.10"):
    return requests.post(f"{API}/keepalive", headers=AUTH, data=json.dumps(_payload(client_id, ip)), timeout=10)


def _hook_bodies():
    out = subprocess.run(
        ["docker", "exec", RECEIVER, "python", "-c", _READ], capture_output=True, text=True, timeout=30, check=True
    )
    return json.loads(out.stdout)["hook"]


def _wait_for(predicate, budget, interval):
    deadline = time.time() + budget
    bodies = []
    while time.time() < deadline:
        bodies = _hook_bodies()
        if any(predicate(b) for b in bodies):
            return bodies, True
        time.sleep(interval)
    return bodies, False


def _new_id():
    return f"e2e-notify-{uuid.uuid4().hex[:8]}"


def test_eviction_alert_reaches_target():
    client_id = _new_id()
    assert _keepalive(client_id).status_code == 200
    # Eviction lands 60 to 120 s after the last keepalive (1 min timeout, 60 s sweep).
    bodies, ok = _wait_for(lambda b: client_id in b and "Went Silent" in b, budget=180, interval=5)
    assert ok, f"no 'Went Silent' alert for {client_id} on /hook within 180 s; got {len(bodies)} bodies"


def test_hung_target_does_not_block_or_starve():
    # Warm-up with a throwaway ID so the server's first public-IP lookup is not timed.
    assert _keepalive(_new_id()).status_code == 200
    client_id = _new_id()
    start = time.time()
    resp = _keepalive(client_id, "203.0.113.11")
    elapsed = time.time() - start
    assert resp.status_code == 200
    assert elapsed < 2, f"keepalive took {elapsed:.2f}s with a hung Apprise target"
    bodies, ok = _wait_for(lambda b: client_id in b and "VPN Connected!" in b, budget=30, interval=2)
    assert ok, f"no 'VPN Connected!' alert for {client_id} on /hook within 30 s; got {len(bodies)} bodies"
