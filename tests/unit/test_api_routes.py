"""
Unit tests for API routes (api_routes.py)
Tests keepalive endpoint, status endpoint, client registration, and data parsing.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import sys
import os

# Add common library to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../vpn_sentinel_common'))

from api_routes import api_app, client_status, _client_first_seen, get_cached_server_ip


@pytest.fixture
def client():
    """Create Flask test client."""
    api_app.config['TESTING'] = True
    with api_app.test_client() as client:
        yield client


@pytest.fixture
def clear_client_data():
    """Clear client data before each test."""
    client_status.clear()
    _client_first_seen.clear()
    yield
    client_status.clear()
    _client_first_seen.clear()


class TestGetStatus:
    """Tests for GET /status endpoint."""
    
    def test_get_status_empty(self, client, clear_client_data):
        """Test status endpoint returns empty dict when no clients."""
        response = client.get('/api/v1/status')
        assert response.status_code == 200
        assert response.json == {}
    
    def test_get_status_with_clients(self, client, clear_client_data):
        """Test status endpoint returns client data."""
        # Add test data
        client_status['test-client'] = {
            'ip': '1.2.3.4',
            'location': 'London, England, GB',
            'last_seen': '2025-11-11T10:00:00'
        }
        
        response = client.get('/api/v1/status')
        assert response.status_code == 200
        assert 'test-client' in response.json
        assert response.json['test-client']['ip'] == '1.2.3.4'


class TestKeepalive:
    """Tests for POST /keepalive endpoint."""
    
    @patch('api_routes.get_cached_server_ip')
    @patch('api_routes.telegram')
    @patch('api_routes.log_info')
    def test_keepalive_flat_format_success(self, mock_log, mock_telegram, mock_server_ip, 
                                           client, clear_client_data):
        """Test keepalive with flat JSON format."""
        mock_server_ip.return_value = '79.116.8.43'
        
        payload = {
            'client_id': 'test-client',
            'public_ip': '91.203.5.146',
            'city': 'London',
            'region': 'England',
            'country': 'GB',
            'provider': 'M247 Ltd',
            'timezone': 'Europe/London',
            'dns_loc': 'GB',
            'dns_colo': 'LHR'
        }
        
        response = client.post('/api/v1/keepalive', json=payload)
        
        assert response.status_code == 200
        assert response.json['status'] == 'ok'
        assert 'server_time' in response.json
        
        # Verify client data stored
        assert 'test-client' in client_status
        assert client_status['test-client']['ip'] == '91.203.5.146'
        assert client_status['test-client']['city'] == 'London'
        assert client_status['test-client']['country'] == 'GB'
        assert client_status['test-client']['dns_loc'] == 'GB'
        
        # Verify Telegram notification sent for new client
        mock_telegram.notify_client_connected.assert_called_once()
    
    @patch('api_routes.get_cached_server_ip')
    @patch('api_routes.telegram')
    @patch('api_routes.log_info')
    def test_keepalive_nested_format_success(self, mock_log, mock_telegram, mock_server_ip,
                                             client, clear_client_data):
        """Test keepalive with nested JSON format."""
        mock_server_ip.return_value = '79.116.8.43'
        
        payload = {
            'client_id': 'test-client',
            'public_ip': '91.203.5.146',
            'location': {
                'city': 'London',
                'region': 'England',
                'country': 'GB',
                'org': 'M247 Ltd',
                'timezone': 'Europe/London'
            },
            'dns_test': {
                'location': 'GB',
                'colo': 'LHR'
            }
        }
        
        response = client.post('/api/v1/keepalive', json=payload)
        
        assert response.status_code == 200
        assert response.json['status'] == 'ok'
        
        # Verify client data stored
        assert 'test-client' in client_status
        assert client_status['test-client']['country'] == 'GB'
        assert client_status['test-client']['dns_loc'] == 'GB'
    
    def test_keepalive_missing_json(self, client, clear_client_data):
        """Test keepalive fails without JSON data."""
        response = client.post('/api/v1/keepalive', 
                               headers={'Content-Type': 'application/json'},
                               data='')
        # Flask returns 500 when get_json fails, but our try/except catches it
        assert response.status_code in [400, 500]
        assert 'error' in response.json
    
    def test_keepalive_missing_client_id(self, client, clear_client_data):
        """Test keepalive fails without client_id."""
        payload = {'public_ip': '1.2.3.4'}
        response = client.post('/api/v1/keepalive', json=payload)
        assert response.status_code == 400
        assert 'error' in response.json
        assert 'client_id is required' in response.json['error']
    
    @patch('api_routes.get_cached_server_ip')
    @patch('api_routes.telegram')
    @patch('api_routes.log_info')
    @patch('api_routes.log_warn')
    def test_keepalive_vpn_bypass_detection(self, mock_log_warn, mock_log, mock_telegram, 
                                            mock_server_ip, client, clear_client_data):
        """Test VPN bypass detection when client IP matches server IP."""
        server_ip = '79.116.8.43'
        mock_server_ip.return_value = server_ip
        
        payload = {
            'client_id': 'bypass-client',
            'public_ip': server_ip,  # Same as server!
            'city': 'Madrid',
            'region': 'Madrid',
            'country': 'ES',
            'provider': 'Hetzner',
            'dns_loc': 'ES'
        }
        
        response = client.post('/api/v1/keepalive', json=payload)
        
        assert response.status_code == 200
        # Verify warning was logged
        mock_log_warn.assert_called()
        args = mock_log_warn.call_args[0]
        assert 'security' in args
        assert 'VPN BYPASS WARNING' in args[1]
    
    @patch('api_routes.get_cached_server_ip')
    @patch('api_routes.telegram')
    @patch('api_routes.log_info')
    def test_keepalive_ip_change_notification(self, mock_log, mock_telegram, mock_server_ip,
                                               client, clear_client_data):
        """Test IP change notification when client IP changes."""
        mock_server_ip.return_value = '79.116.8.43'
        
        # First keepalive
        payload1 = {
            'client_id': 'test-client',
            'public_ip': '1.2.3.4',
            'city': 'London',
            'country': 'GB',
            'dns_loc': 'GB'
        }
        client.post('/api/v1/keepalive', json=payload1)
        
        # Second keepalive with different IP
        payload2 = {
            'client_id': 'test-client',
            'public_ip': '5.6.7.8',  # Changed!
            'city': 'Paris',
            'country': 'FR',
            'dns_loc': 'FR'
        }
        response = client.post('/api/v1/keepalive', json=payload2)
        
        assert response.status_code == 200
        
        # Verify IP change notification sent
        mock_telegram.notify_ip_changed.assert_called_once()
        args = mock_telegram.notify_ip_changed.call_args[0]
        assert args[0] == 'test-client'
        assert args[1] == '1.2.3.4'  # Old IP
        assert args[2] == '5.6.7.8'  # New IP
    
    @patch('api_routes.get_cached_server_ip')
    @patch('api_routes.telegram')
    @patch('api_routes.log_info')
    def test_keepalive_defaults_for_missing_fields(self, mock_log, mock_telegram, mock_server_ip,
                                                    client, clear_client_data):
        """Test keepalive uses defaults for missing optional fields."""
        mock_server_ip.return_value = '79.116.8.43'
        
        payload = {
            'client_id': 'minimal-client',
            'public_ip': '1.2.3.4'
            # Missing: city, region, country, provider, timezone, dns_loc
        }
        
        response = client.post('/api/v1/keepalive', json=payload)
        
        assert response.status_code == 200
        
        # Verify defaults applied
        assert client_status['minimal-client']['city'] == 'unknown'
        assert client_status['minimal-client']['country'] == 'unknown'
        assert client_status['minimal-client']['dns_loc'] == 'Unknown'
    
    @patch('api_routes.get_cached_server_ip')
    @patch('api_routes.telegram')
    @patch('api_routes.log_info')
    def test_keepalive_handles_ip_field_fallback(self, mock_log, mock_telegram, mock_server_ip,
                                                  client, clear_client_data):
        """Test keepalive falls back to 'ip' field if 'public_ip' not present."""
        mock_server_ip.return_value = '79.116.8.43'
        
        payload = {
            'client_id': 'test-client',
            'ip': '1.2.3.4',  # Using 'ip' instead of 'public_ip'
            'country': 'GB'
        }
        
        response = client.post('/api/v1/keepalive', json=payload)
        
        assert response.status_code == 200
        assert client_status['test-client']['ip'] == '1.2.3.4'
    
    @patch('api_routes.client_status')
    @patch('api_routes.get_cached_server_ip')
    @patch('api_routes.log_info')
    def test_keepalive_exception_handling(self, mock_log, mock_server_ip, mock_client_status,
                                          client, clear_client_data):
        """Test keepalive handles exceptions gracefully."""
        # Mock client_status to raise exception during update
        mock_server_ip.return_value = '79.116.8.43'
        mock_client_status.__setitem__.side_effect = Exception("Test error")
        
        response = client.post('/api/v1/keepalive', json={'client_id': 'test', 'public_ip': '1.2.3.4'})
        
        # Should return 500 for internal errors
        assert response.status_code == 500
        assert 'error' in response.json


class TestGetCachedServerIp:
    """Tests for get_cached_server_ip function."""
    
    @patch('api_routes.get_server_public_ip')
    def test_caches_server_ip(self, mock_get_ip):
        """Test server IP is cached after first call."""
        mock_get_ip.return_value = '79.116.8.43'
        
        # Reset cache
        import api_routes
        api_routes._server_public_ip = None
        
        # First call should fetch
        ip1 = get_cached_server_ip()
        assert ip1 == '79.116.8.43'
        assert mock_get_ip.call_count == 1
        
        # Second call should use cache
        ip2 = get_cached_server_ip()
        assert ip2 == '79.116.8.43'
        assert mock_get_ip.call_count == 1  # Not called again


class TestApiPath:
    """Tests for API_PATH configuration."""
    
    def test_api_path_from_environment(self):
        """Test API_PATH is read from environment."""
        from api_routes import API_PATH
        # Should be /api/v1 or custom from VPN_SENTINEL_API_PATH env var
        assert API_PATH.startswith('/')
        assert len(API_PATH) > 1
