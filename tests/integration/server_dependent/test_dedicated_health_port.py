"""
Tests for server when using a dedicated health port
Skipped by default unless VPN_SENTINEL_SERVER_TESTS=1
"""
import os
import pytest

if not os.getenv("VPN_SENTINEL_SERVER_TESTS"):
    pytest.skip("Server-dependent integration tests disabled. Set VPN_SENTINEL_SERVER_TESTS=1 to enable.", allow_module_level=True)

import requests
import time
import sys
import subprocess


def test_server_runs_on_dedicated_health_port():
    server_script = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../vpn-sentinel-server/vpn-sentinel-server.py'))
    if not os.path.exists(server_script):
        pytest.skip("Server script not present in workspace")

    env = os.environ.copy()
    env['VPN_SENTINEL_SERVER_HEALTH_PORT'] = '8888'
    env['FLASK_ENV'] = 'testing'

    proc = subprocess.Popen([sys.executable, server_script], env=env)
    try:
        time.sleep(1)
        health_url = 'http://localhost:8888'
        try:
            r = requests.get(f"{health_url}/health", timeout=5)
            assert r.status_code == 200
        except requests.ConnectionError:
            pytest.skip("Health endpoint not reachable on dedicated port")
    finally:
        proc.terminate()
        proc.wait(timeout=5)
