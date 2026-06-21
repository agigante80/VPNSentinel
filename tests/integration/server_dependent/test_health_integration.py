"""
Server health integration tests (server-dependent)
Skipped by default. Set VPN_SENTINEL_SERVER_TESTS=1 to enable.
"""
import os
import pytest

if not os.getenv("VPN_SENTINEL_SERVER_TESTS"):
    pytest.skip("Server-dependent integration tests disabled. Set VPN_SENTINEL_SERVER_TESTS=1 to enable.", allow_module_level=True)

import requests
import time
import subprocess
import sys


def test_health_endpoints_available():
    health_url = os.getenv('VPN_SENTINEL_HEALTH_URL', 'http://localhost:8081')
    try:
        r = requests.get(f"{health_url}/health", timeout=5)
        assert r.status_code == 200
    except requests.ConnectionError:
        pytest.skip("Health endpoint not available; server likely not running")


def test_ready_and_startup():
    health_url = os.getenv('VPN_SENTINEL_HEALTH_URL', 'http://localhost:8081')
    try:
        r_ready = requests.get(f"{health_url}/health/ready", timeout=5)
        r_startup = requests.get(f"{health_url}/health/startup", timeout=5)
        assert r_ready.status_code in (200, 503)
        assert r_startup.status_code in (200, 503)
    except requests.ConnectionError:
        pytest.skip("Health endpoints not reachable; server not running")


def test_server_process_start_and_stop():
    """Try starting the server process and ensuring health endpoint appears"""
    pytest.skip("Server script deleted during refactor - need to create new entrypoint")
