"""Live-stack E2E for file-based secrets (issue #139).

Runs only when VPN_SENTINEL_E2E=1 (set by `bin/local-env verify`). The test stack mounts the API key
as a Docker secret file on BOTH services (see tests/docker-compose.test.yaml), so the existing E2E suite
already proves the client and server read it. These tests pin the observable auth behaviour and the
fail-closed startup.
"""

import json
import os
import shutil
import subprocess

import pytest
import requests

E2E_ENABLED = os.getenv("VPN_SENTINEL_E2E") == "1"

HOST = os.getenv("VPN_SENTINEL_SERVER_HOST", "localhost")
API_PORT = os.getenv("VPN_SENTINEL_E2E_API_PORT", "15554")
API_PATH = os.getenv("VPN_SENTINEL_API_PATH", "/test/v1")
API_KEY = os.getenv("VPN_SENTINEL_API_KEY", "test-api-key-abcdef123456789")
API = f"http://{HOST}:{API_PORT}{API_PATH}"
COMPOSE_FILE = os.path.join(os.path.dirname(__file__), "..", "docker-compose.test.yaml")

pytestmark = pytest.mark.skipif(
    not E2E_ENABLED,
    reason="Set VPN_SENTINEL_E2E=1 (via `bin/local-env verify`) to run live-stack E2E.",
)


def _payload(client_id):
    return {
        "client_id": client_id,
        "timestamp": "2026-06-21T00:00:00+00:00",
        "public_ip": "203.0.113.20",
        "status": "alive",
        "location": {"country": "US", "city": "X", "region": "Y", "org": "AS1 Z", "timezone": "UTC"},
        "dns_test": {"location": "US", "colo": "NYC"},
    }


def _post(headers):
    return requests.post(
        f"{API}/keepalive",
        headers={"Content-Type": "application/json", **headers},
        data=json.dumps(_payload("secret-e2e")),
        timeout=30,
    )


def test_keepalive_with_file_key_is_accepted():
    assert _post({"X-API-Key": API_KEY}).status_code == 200


def test_keepalive_without_key_is_401():
    assert _post({}).status_code == 401


def test_keepalive_with_wrong_key_is_403():
    assert _post({"X-API-Key": "wrong-key"}).status_code == 403


@pytest.mark.skipif(shutil.which("docker") is None, reason="docker not on PATH")
def test_unreadable_key_file_stops_server_with_exit_1():
    cmd = [
        "docker",
        "compose",
        "-f",
        COMPOSE_FILE,
        "run",
        "--rm",
        "--no-deps",
        "-e",
        "VPN_SENTINEL_API_KEY=",
        "-e",
        "VPN_SENTINEL_API_KEY_FILE=/run/secrets/missing",
        "vpn-sentinel-server-test",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    out = r.stdout + r.stderr
    assert r.returncode == 1, out
    assert "cannot be read" in out
