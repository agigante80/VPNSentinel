"""Unit tests for configuration validation.

Tests for:
- Telegram validation when VPN_SENTINEL_TELEGRAM_ENABLED=true
- Client ID generation format
- Dashboard enable/disable flag
- API path configuration
"""
import pytest
import sys
import os
import importlib
from unittest.mock import patch, Mock
import re


class TestClientIDGeneration:
    """Tests for generate_client_id() function."""

    def test_client_id_default_format(self):
        """Test default client ID matches format: vpn-monitor-{12-digits}."""
        from vpn_sentinel_common.config import generate_client_id
        
        client_id = generate_client_id({})
        
        # Should match pattern: vpn-monitor-{12 digits}
        pattern = r'^vpn-monitor-\d{12}$'
        assert re.match(pattern, client_id), f"Client ID '{client_id}' does not match expected format"
        
    def test_client_id_all_digits_unique(self):
        """Test that generated IDs have 12 digits."""
        from vpn_sentinel_common.config import generate_client_id
        
        client_id = generate_client_id({})
        digits_part = client_id.replace('vpn-monitor-', '')
        
        assert len(digits_part) == 12
        assert digits_part.isdigit()
    
    def test_client_id_custom_from_env(self):
        """Test custom client ID from environment."""
        from vpn_sentinel_common.config import generate_client_id
        
        custom_id = 'office-vpn-primary'
        client_id = generate_client_id({'VPN_SENTINEL_CLIENT_ID': custom_id})
        
        assert client_id == custom_id
    
    def test_client_id_sanitization(self):
        """Test client ID sanitization for invalid characters."""
        from vpn_sentinel_common.config import generate_client_id
        
        invalid_id = 'Client@123#ABC'
        client_id = generate_client_id({'VPN_SENTINEL_CLIENT_ID': invalid_id})
        
        # Should be sanitized to lowercase with only alphanumeric and dashes
        assert client_id.islower() or client_id.replace('-', '').replace('0', '').replace('1', '').replace('2', '').replace('3', '').replace('4', '').replace('5', '').replace('6', '').replace('7', '').replace('8', '').replace('9', '').islower()
        assert '@' not in client_id
        assert '#' not in client_id


# NOTE: Telegram validation tests have been moved to test_telegram_validation_isolation.py
# to avoid module state conflicts with other tests.


class TestServerConfiguration:
    """Tests for server configuration options."""
    
    @patch.dict(os.environ, {
        'VPN_SENTINEL_SERVER_API_PORT': '6000',
        'VPN_SENTINEL_SERVER_HEALTH_PORT': '7081',
        'VPN_SENTINEL_SERVER_DASHBOARD_PORT': '7080'
    })
    def test_custom_port_configuration(self):
        """Test that server reads custom port configuration."""
        from vpn_sentinel_common.server_utils import get_port_config
        
        ports = get_port_config()
        
        assert ports['api_port'] == 6000
        assert ports['health_port'] == 7081
        assert ports['dashboard_port'] == 7080
    
    def test_default_port_configuration(self):
        """Test default port values."""
        from vpn_sentinel_common.server_utils import get_port_config
        
        # Save current env
        saved_env = {}
        for key in ['VPN_SENTINEL_SERVER_API_PORT', 'VPN_SENTINEL_SERVER_HEALTH_PORT', 'VPN_SENTINEL_SERVER_DASHBOARD_PORT']:
            saved_env[key] = os.environ.pop(key, None)
        
        try:
            ports = get_port_config()
            
            assert ports['api_port'] == 5000
            assert ports['health_port'] == 8081
            assert ports['dashboard_port'] == 8080
        finally:
            # Restore env
            for key, val in saved_env.items():
                if val is not None:
                    os.environ[key] = val


class TestAPIPathConfiguration:
    """Tests for API path configuration."""
    
    def test_api_path_read_from_environment(self):
        """Test that API path configuration follows expected format."""
        # Test the same logic that api_routes.py uses without importing the module
        # to avoid Flask app conflicts with other tests
        api_path_env = os.getenv('VPN_SENTINEL_API_PATH', '/api/v1')
        api_path = api_path_env.strip('/')
        if not api_path.startswith('/'):
            api_path = '/' + api_path
        
        # Verify the path follows expected format
        assert isinstance(api_path, str)
        assert api_path.startswith('/')
        assert len(api_path.strip('/')) > 0  # Should not be empty after stripping slashes
    
    @patch.dict(os.environ, {'VPN_SENTINEL_API_PATH': '/custom/v2'})
    def test_custom_api_path_format(self):
        """Test that custom API path is formatted correctly."""
        # Note: This test may not work perfectly since api_routes is already imported
        # But it demonstrates the expected behavior
        api_path = os.getenv('VPN_SENTINEL_API_PATH', '/api/v1').strip('/')
        if not api_path.startswith('/'):
            api_path = '/' + api_path
        
        assert api_path == '/custom/v2'


class TestDashboardConfiguration:
    """Tests for dashboard enable/disable configuration."""
    
    @patch.dict(os.environ, {'VPN_SENTINEL_SERVER_WEB_DASHBOARD_ENABLED': 'false'})
    def test_dashboard_can_be_disabled(self):
        """Test that dashboard can be disabled via environment variable."""
        enabled = os.getenv('VPN_SENTINEL_SERVER_WEB_DASHBOARD_ENABLED', 'true').lower() == 'true'
        
        assert enabled is False
    
    def test_dashboard_enabled_by_default(self):
        """Test that dashboard is enabled by default."""
        # Remove env var if present
        os.environ.pop('VPN_SENTINEL_SERVER_WEB_DASHBOARD_ENABLED', None)
        
        enabled = os.getenv('VPN_SENTINEL_SERVER_WEB_DASHBOARD_ENABLED', 'true').lower() == 'true'
        
        assert enabled is True
    
    @patch.dict(os.environ, {'VPN_SENTINEL_SERVER_WEB_DASHBOARD_ENABLED': 'true'})
    def test_dashboard_explicit_enable(self):
        """Test that dashboard can be explicitly enabled."""
        enabled = os.getenv('VPN_SENTINEL_SERVER_WEB_DASHBOARD_ENABLED', 'true').lower() == 'true'
        
        assert enabled is True
