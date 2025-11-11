"""
Unit tests for Health routes (health_routes.py)
Tests health check endpoints.
"""
import pytest
import sys
import os

# Add common library to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from vpn_sentinel_common.health_routes import health_app


@pytest.fixture
def client():
    """Create Flask test client."""
    health_app.config['TESTING'] = True
    with health_app.test_client() as client:
        yield client


class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    def test_health_endpoint(self, client):
        """Test basic /health endpoint."""
        response = client.get('/health')
        
        assert response.status_code == 200
        assert response.json['status'] == 'ok'
        assert 'message' in response.json
        assert 'Health Server is running' in response.json['message']
    
    def test_health_ready_endpoint(self, client):
        """Test /health/ready endpoint."""
        response = client.get('/health/ready')
        
        assert response.status_code == 200
        assert response.json['status'] == 'ok'
        assert 'ready' in response.json['message']
    
    def test_health_startup_endpoint(self, client):
        """Test /health/startup endpoint."""
        response = client.get('/health/startup')
        
        assert response.status_code == 200
        assert response.json['status'] == 'ok'
        assert 'started' in response.json['message']
    
    def test_all_health_endpoints_return_json(self, client):
        """Test all health endpoints return valid JSON."""
        endpoints = ['/health', '/health/ready', '/health/startup']
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.content_type == 'application/json'
            assert 'status' in response.json
            assert 'message' in response.json
