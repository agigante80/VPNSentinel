"""
Simple test to verify health app functionality (server-dependent)
Skipped by default. Set VPN_SENTINEL_SERVER_TESTS=1 to enable.
"""
import os
import sys
import json
import pytest

if not os.getenv("VPN_SENTINEL_SERVER_TESTS"):
    pytest.skip("Server-dependent integration tests disabled. Set VPN_SENTINEL_SERVER_TESTS=1 to enable.", allow_module_level=True)

# Add project paths (relative to this file)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'vpn-sentinel-server'))


def test_health_app():
    """Test the health app functionality by importing the Flask test client"""
    try:
        # Import from the common server module
        from vpn_sentinel_common.server import health_app

        # Configure for testing
        health_app.config['TESTING'] = True
        client = health_app.test_client()

        # Test main health endpoint
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'server_time' in data
        assert 'system' in data

        # Test readiness endpoint
        response = client.get('/health/ready')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ready'
        assert 'checks' in data

        # Test startup endpoint
        response = client.get('/health/startup')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'started'
        assert 'server_time' in data

        # Test wrong methods
        response = client.post('/health')
        assert response.status_code == 405

        # Test invalid paths
        response = client.get('/health/invalid')
        assert response.status_code == 404

    except Exception:
        # Re-raise so pytest reports traceback
        raise
