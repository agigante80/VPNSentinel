#!/usr/bin/env python3
"""
Simple test script to verify dedicated health port functionality
"""
import os
import sys
import json

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'vpn-sentinel-server'))

def test_health_app():
    """Test the health app functionality"""
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

if __name__ == '__main__':
    success = test_health_app()
    sys.exit(0 if success else 1)