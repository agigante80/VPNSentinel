"""
Client multi-process integration tests that require a running server or Docker
Skipped by default. Enable with VPN_SENTINEL_SERVER_TESTS=1
"""
import os
import pytest

if not os.getenv("VPN_SENTINEL_SERVER_TESTS"):
    pytest.skip("Server-dependent integration tests disabled. Set VPN_SENTINEL_SERVER_TESTS=1 to enable.", allow_module_level=True)

import subprocess
import sys
import time
import requests


def test_multiple_clients_register_and_listed():
    server_url = os.getenv('VPN_SENTINEL_URL', 'http://localhost:5000')
    api_path = os.getenv('VPN_SENTINEL_API_PATH', '/api/v1')
    api_key = os.getenv('VPN_SENTINEL_API_KEY', 'test-api-key-abcdef123456789')

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    # This test requires the server to be running and accepting keepalives
    try:
        # Send two keepalive requests from different client IDs
        payload1 = {
            'client_id': 'multi-client-1',
            'timestamp': time.time(),
            'public_ip': '203.0.113.10'
        }
        payload2 = {
            'client_id': 'multi-client-2',
            'timestamp': time.time(),
            'public_ip': '203.0.113.11'
        }
        r1 = requests.post(f"{server_url}{api_path}/keepalive", headers=headers, json=payload1, timeout=5)
        r2 = requests.post(f"{server_url}{api_path}/keepalive", headers=headers, json=payload2, timeout=5)

        if r1.status_code != 200 or r2.status_code != 200:
            pytest.skip("Server did not accept keepalive requests (not running or misconfigured)")

        # Now query server status
        r_status = requests.get(f"{server_url}{api_path}/status", headers=headers, timeout=5)
        if r_status.status_code != 200:
            pytest.skip("Server status endpoint not available")

        status_data = r_status.json()
        assert 'multi-client-1' in status_data
        assert 'multi-client-2' in status_data

    except requests.ConnectionError:
        pytest.skip("Server not running for integration tests")
