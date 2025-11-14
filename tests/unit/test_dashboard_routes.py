"""
Unit tests for Dashboard routes (dashboard_routes.py)
Tests dashboard rendering, client health status, traffic light logic.
"""
import pytest
from unittest.mock import patch, MagicMock, Mock
import sys
import os

# Add common library to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../vpn_sentinel_common'))

# Mock api_routes to prevent Flask route registration conflicts
# This must be done BEFORE importing dashboard_routes
mock_api_routes = Mock()
mock_api_routes.client_status = {}

with patch.dict('sys.modules', {'vpn_sentinel_common.api_routes': mock_api_routes}):
    import dashboard_routes
    from dashboard_routes import dashboard_app, get_client_health_status


@pytest.fixture
def client():
    """Create Flask test client."""
    dashboard_app.config['TESTING'] = True
    with dashboard_app.test_client() as client:
        yield client


class TestGetClientHealthStatus:
    """Tests for get_client_health_status function."""
    
    def test_status_danger_same_ip(self):
        """Test RED status when client IP matches server IP (VPN bypass)."""
        server_ip = '79.116.8.43'
        client = {
            'ip': '79.116.8.43',  # Same as server
            'country': 'ES',
            'dns_loc': 'ES'
        }
        
        status_class, icon, text, dns_icon = get_client_health_status(client, server_ip)
        
        assert status_class == 'status-danger'
        assert '🔴' in icon
        assert 'VPN Bypass' in text
    
    def test_status_danger_unknown_ip(self):
        """Test RED status when client IP is unknown."""
        server_ip = '79.116.8.43'
        client = {
            'ip': 'unknown',
            'country': 'US',
            'dns_loc': 'US'
        }
        
        status_class, icon, text, dns_icon = get_client_health_status(client, server_ip)
        
        assert status_class == 'status-danger'
        assert '🔴' in icon
    
    def test_status_warning_dns_leak(self):
        """Test YELLOW status when DNS location differs from country (DNS leak)."""
        server_ip = '79.116.8.43'
        client = {
            'ip': '91.203.5.146',  # Different from server
            'country': 'GB',
            'dns_loc': 'US'  # Different from country!
        }
        
        status_class, icon, text, dns_icon = get_client_health_status(client, server_ip)
        
        assert status_class == 'status-warning'
        assert '🟡' in icon
        assert 'DNS Leak' in text
    
    def test_status_warning_dns_unknown(self):
        """Test YELLOW status when DNS location is unknown."""
        server_ip = '79.116.8.43'
        client = {
            'ip': '91.203.5.146',
            'country': 'GB',
            'dns_loc': 'Unknown'  # DNS undetectable
        }
        
        status_class, icon, text, dns_icon = get_client_health_status(client, server_ip)
        
        assert status_class == 'status-warning'
        assert '🟡' in icon
        assert 'Undetectable' in text
    
    def test_status_ok_secure(self):
        """Test GREEN status when VPN is working correctly."""
        server_ip = '79.116.8.43'
        client = {
            'ip': '91.203.5.146',  # Different from server
            'country': 'GB',
            'dns_loc': 'GB'  # Matches country
        }
        
        status_class, icon, text, dns_icon = get_client_health_status(client, server_ip)
        
        assert status_class == 'status-ok'
        assert '🟢' in icon
        assert 'Secure' in text
    
    def test_defaults_for_missing_fields(self):
        """Test defaults are used for missing client fields."""
        server_ip = '79.116.8.43'
        client = {}  # No fields
        
        status_class, icon, text, dns_icon = get_client_health_status(client, server_ip)
        
        # Should default to danger (unknown IP)
        assert status_class == 'status-danger'
    
    def test_case_sensitivity_unknown_ip(self):
        """Test that both 'unknown' and 'Unknown' trigger danger status."""
        server_ip = '79.116.8.43'
        
        # Test lowercase 'unknown'
        client1 = {'ip': 'unknown', 'country': 'US', 'dns_loc': 'US'}
        status1, _, _, _ = get_client_health_status(client1, server_ip)
        assert status1 == 'status-danger'
        
        # Test capitalized 'Unknown'
        client2 = {'ip': 'Unknown', 'country': 'US', 'dns_loc': 'US'}
        status2, _, _, _ = get_client_health_status(client2, server_ip)
        assert status2 == 'status-danger'


class TestDashboardRoute:
    """Tests for /dashboard route."""
    
    @pytest.mark.skip(reason="Flask route conflicts - requires refactoring")
    @patch('dashboard_routes.get_server_info')
    @patch('dashboard_routes.client_status', {})
    def test_dashboard_no_clients(self, mock_server_info, client):
        """Test dashboard renders correctly with no clients."""
        mock_server_info.return_value = {
            'public_ip': '79.116.8.43',
            'location': 'Madrid, ES',
            'provider': 'Hetzner',
            'dns_status': 'OK'
        }
        
        response = client.get('/dashboard')
        
        assert response.status_code == 200
        assert b'No VPN Clients Connected' in response.data
        assert b'Waiting for VPN clients' in response.data
    
    @pytest.mark.skip(reason="Flask route conflicts - requires refactoring")
    @patch('dashboard_routes.get_server_info')
    @patch('dashboard_routes.client_status')
    def test_dashboard_with_clients(self, mock_client_status, mock_server_info, client):
        """Test dashboard renders correctly with connected clients."""
        mock_server_info.return_value = {
            'public_ip': '79.116.8.43',
            'location': 'Madrid, ES',
            'provider': 'Hetzner',
            'dns_status': 'OK'
        }
        
        mock_client_status.__bool__ = lambda self: True
        mock_client_status.__len__ = lambda self: 2
        mock_client_status.values.return_value = [
            {'ip': '1.2.3.4'},
            {'ip': '5.6.7.8'}
        ]
        mock_client_status.items.return_value = [
            ('client-1', {
                'ip': '91.203.5.146',
                'location': 'London, England, GB',
                'provider': 'M247 Ltd',
                'last_seen': '2025-11-11T10:00:00',
                'country': 'GB',
                'dns_loc': 'GB',
                'dns_colo': 'LHR'
            }),
            ('client-2', {
                'ip': '45.142.120.50',
                'location': 'Frankfurt, Hessen, DE',
                'provider': 'M247 Ltd',
                'last_seen': '2025-11-11T10:00:00',
                'country': 'DE',
                'dns_loc': 'DE',
                'dns_colo': 'FRA'
            })
        ]
        
        response = client.get('/dashboard')
        
        assert response.status_code == 200
        assert b'client-1' in response.data
        assert b'client-2' in response.data
        assert b'London' in response.data
        assert b'Frankfurt' in response.data
        assert b'M247 Ltd' in response.data
    
    @pytest.mark.skip(reason="Flask route conflicts - requires refactoring")
    @patch('dashboard_routes.get_server_info')
    @patch('dashboard_routes.client_status')
    def test_dashboard_shows_status_badges(self, mock_client_status, mock_server_info, client):
        """Test dashboard shows correct status badges for different client states."""
        mock_server_info.return_value = {
            'public_ip': '79.116.8.43',
            'location': 'Madrid, ES',
            'provider': 'Hetzner',
            'dns_status': 'OK'
        }
        
        mock_client_status.__bool__ = lambda self: True
        mock_client_status.__len__ = lambda self: 3
        mock_client_status.values.return_value = [
            {'ip': '1.2.3.4'}, 
            {'ip': '5.6.7.8'},
            {'ip': '9.10.11.12'}
        ]
        mock_client_status.items.return_value = [
            ('secure-client', {
                'ip': '91.203.5.146',
                'location': 'London, GB',
                'provider': 'M247',
                'last_seen': '2025-11-11T10:00:00',
                'country': 'GB',
                'dns_loc': 'GB',  # Secure
                'dns_colo': 'LHR'
            }),
            ('leaked-client', {
                'ip': '45.142.120.50',
                'location': 'Frankfurt, DE',
                'provider': 'M247',
                'last_seen': '2025-11-11T10:00:00',
                'country': 'DE',
                'dns_loc': 'US',  # DNS leak!
                'dns_colo': 'FRA'
            }),
            ('bypass-client', {
                'ip': '79.116.8.43',  # Same as server!
                'location': 'Madrid, ES',
                'provider': 'Hetzner',
                'last_seen': '2025-11-11T10:00:00',
                'country': 'ES',
                'dns_loc': 'ES',
                'dns_colo': 'MAD'
            })
        ]
        
        response = client.get('/dashboard')
        
        assert response.status_code == 200
        # Check for status badges
        assert b'status-ok' in response.data  # Green
        assert b'status-warning' in response.data  # Yellow
        assert b'status-danger' in response.data  # Red
        assert b'Secure' in response.data
        assert b'DNS Leak' in response.data
        assert b'VPN Bypass' in response.data
    
    @pytest.mark.skip(reason="Flask route conflicts - requires refactoring")
    @patch('dashboard_routes.get_server_info')
    @patch('dashboard_routes.client_status')
    def test_dashboard_time_formatting(self, mock_client_status, mock_server_info, client):
        """Test dashboard formats 'last seen' times correctly."""
        from datetime import datetime, timedelta
        
        mock_server_info.return_value = {
            'public_ip': '79.116.8.43',
            'location': 'Madrid, ES',
            'provider': 'Hetzner',
            'dns_status': 'OK'
        }
        
        # Create timestamps for different time periods
        now = datetime.utcnow()
        recent = (now - timedelta(seconds=30)).isoformat()
        minutes_ago = (now - timedelta(minutes=5)).isoformat()
        hours_ago = (now - timedelta(hours=2)).isoformat()
        
        mock_client_status.__bool__ = lambda self: True
        mock_client_status.__len__ = lambda self: 3
        mock_client_status.values.return_value = [{'ip': '1.2.3.4'}] * 3
        mock_client_status.items.return_value = [
            ('recent-client', {
                'ip': '1.2.3.4',
                'location': 'London, GB',
                'provider': 'M247',
                'last_seen': recent,
                'country': 'GB',
                'dns_loc': 'GB',
                'dns_colo': 'LHR'
            }),
            ('minutes-client', {
                'ip': '1.2.3.5',
                'location': 'London, GB',
                'provider': 'M247',
                'last_seen': minutes_ago,
                'country': 'GB',
                'dns_loc': 'GB',
                'dns_colo': 'LHR'
            }),
            ('hours-client', {
                'ip': '1.2.3.6',
                'location': 'London, GB',
                'provider': 'M247',
                'last_seen': hours_ago,
                'country': 'GB',
                'dns_loc': 'GB',
                'dns_colo': 'LHR'
            })
        ]
        
        response = client.get('/dashboard')
        
        assert response.status_code == 200
        assert b'Just now' in response.data
        assert b'min ago' in response.data
        assert b'h ago' in response.data
    
    @pytest.mark.skip(reason="Flask route conflicts - requires refactoring")
    @patch('dashboard_routes.get_server_info')
    @patch('dashboard_routes.client_status', {})
    @patch.dict(os.environ, {'VPN_SENTINEL_VERSION': 'v1.2.3'})
    def test_dashboard_shows_version(self, mock_server_info, client):
        """Test dashboard displays version from environment variable."""
        mock_server_info.return_value = {
            'public_ip': '79.116.8.43',
            'location': 'Madrid, ES',
            'provider': 'Hetzner',
            'dns_status': 'OK'
        }
        
        response = client.get('/dashboard')
        
        assert response.status_code == 200
        assert b'v1.2.3' in response.data
    
    @pytest.mark.skip(reason="Flask route conflicts - requires refactoring")
    @patch('dashboard_routes.get_server_info')
    @patch('dashboard_routes.client_status')
    def test_dashboard_shows_server_info(self, mock_client_status, mock_server_info, client):
        """Test dashboard displays server information."""
        mock_server_info.return_value = {
            'public_ip': '79.116.8.43',
            'location': 'Madrid, Madrid, ES',
            'provider': 'Hetzner Online GmbH',
            'dns_status': 'OK'
        }
        
        mock_client_status.__bool__ = lambda self: False
        mock_client_status.__len__ = lambda self: 0
        mock_client_status.values.return_value = []
        
        response = client.get('/dashboard')
        
        assert response.status_code == 200
        assert b'79.116.8.43' in response.data
        assert b'Madrid' in response.data
        assert b'Hetzner' in response.data


class TestLogsEndpoint:
    """Tests for /logs endpoint."""
    
    def test_logs_endpoint_exists(self, client):
        """Test /logs endpoint is accessible."""
        response = client.get('/logs')
        assert response.status_code == 200
    
    def test_logs_endpoint_returns_html(self, client):
        """Test /logs endpoint returns HTML content."""
        response = client.get('/logs')
        assert response.status_code == 200
        assert b'<!DOCTYPE html>' in response.data or b'<html' in response.data
    
    @patch.dict('os.environ', {'VPN_SENTINEL_LOG_FILE': '/tmp/test-sentinel.log'})
    def test_logs_uses_env_log_file(self, client):
        """Test /logs uses VPN_SENTINEL_LOG_FILE environment variable."""
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write("2025-11-14T17:00:00Z INFO [test] Test log message\n")
            temp_path = f.name
        
        try:
            with patch.dict('os.environ', {'VPN_SENTINEL_LOG_FILE': temp_path}):
                response = client.get('/logs')
                assert response.status_code == 200
                assert b'Test log message' in response.data
        finally:
            os.unlink(temp_path)
    
    def test_logs_displays_no_file_message(self, client):
        """Test /logs displays message when no log file is found."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('os.path.exists', return_value=False):
                response = client.get('/logs')
                assert response.status_code == 200
                assert b'No log file' in response.data or b'not found' in response.data
    
    def test_logs_shows_formatted_logs(self, client):
        """Test /logs displays formatted log entries."""
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write("2025-11-14T17:00:00Z INFO [api] 🌐 127.0.0.1 \"GET /health\" 200\n")
            f.write("2025-11-14T17:00:01Z WARN [security] ⚠️ Test warning\n")
            f.write("2025-11-14T17:00:02Z ERROR [server] ❌ Test error\n")
            temp_path = f.name
        
        try:
            with patch.dict('os.environ', {'VPN_SENTINEL_LOG_FILE': temp_path}):
                response = client.get('/logs')
                assert response.status_code == 200
                # Check for log content
                assert b'127.0.0.1' in response.data
                assert b'Test warning' in response.data
                assert b'Test error' in response.data
        finally:
            os.unlink(temp_path)
    
    def test_logs_auto_refresh_enabled(self, client):
        """Test /logs includes auto-refresh functionality."""
        response = client.get('/logs')
        assert response.status_code == 200
        # Check for auto-refresh meta tag or JavaScript
        assert b'refresh' in response.data.lower() or b'setInterval' in response.data
    
    def test_logs_file_statistics(self, client):
        """Test /logs displays file statistics."""
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            for i in range(10):
                f.write(f"2025-11-14T17:00:{i:02d}Z INFO [test] Line {i}\n")
            temp_path = f.name
        
        try:
            with patch.dict('os.environ', {'VPN_SENTINEL_LOG_FILE': temp_path}):
                response = client.get('/logs')
                assert response.status_code == 200
                # Check for file info
                assert b'lines' in response.data.lower() or b'bytes' in response.data.lower()
        finally:
            os.unlink(temp_path)
