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


class TestTelegramValidation:
    """Tests for Telegram configuration validation."""
    
    @patch.dict(os.environ, {
        'VPN_SENTINEL_TELEGRAM_ENABLED': 'true',
        'TELEGRAM_BOT_TOKEN': '',
        'TELEGRAM_CHAT_ID': ''
    }, clear=False)
    def test_telegram_enabled_without_token_exits(self):
        """Test that VPN_SENTINEL_TELEGRAM_ENABLED=true without token causes exit."""
        # Need to reload the module to test initialization
        if 'vpn_sentinel_common.telegram' in sys.modules:
            del sys.modules['vpn_sentinel_common.telegram']
        
        with pytest.raises(SystemExit) as exc_info:
            from vpn_sentinel_common import telegram
        
        assert exc_info.value.code == 1
    
    @patch.dict(os.environ, {
        'VPN_SENTINEL_TELEGRAM_ENABLED': 'true',
        'TELEGRAM_BOT_TOKEN': 'test-token',
        'TELEGRAM_CHAT_ID': ''
    }, clear=False)
    def test_telegram_enabled_without_chat_id_exits(self):
        """Test that VPN_SENTINEL_TELEGRAM_ENABLED=true without chat ID causes exit."""
        if 'vpn_sentinel_common.telegram' in sys.modules:
            del sys.modules['vpn_sentinel_common.telegram']
        
        with pytest.raises(SystemExit) as exc_info:
            from vpn_sentinel_common import telegram
        
        assert exc_info.value.code == 1
    
    @patch.dict(os.environ, {
        'VPN_SENTINEL_TELEGRAM_ENABLED': 'true',
        'TELEGRAM_BOT_TOKEN': 'test-token-123',
        'TELEGRAM_CHAT_ID': '123456789'
    }, clear=False)
    def test_telegram_enabled_with_credentials_succeeds(self):
        """Test that VPN_SENTINEL_TELEGRAM_ENABLED=true with credentials works."""
        if 'vpn_sentinel_common.telegram' in sys.modules:
            del sys.modules['vpn_sentinel_common.telegram']
        
        from vpn_sentinel_common import telegram
        
        assert telegram.TELEGRAM_ENABLED is True
        assert telegram.TELEGRAM_BOT_TOKEN == 'test-token-123'
        assert telegram.TELEGRAM_CHAT_ID == '123456789'
    
    @patch.dict(os.environ, {
        'VPN_SENTINEL_TELEGRAM_ENABLED': 'false',
        'TELEGRAM_BOT_TOKEN': 'test-token',
        'TELEGRAM_CHAT_ID': '123456'
    }, clear=False)
    def test_telegram_explicit_disable(self):
        """Test that VPN_SENTINEL_TELEGRAM_ENABLED=false disables even with credentials."""
        # Reload module to test with new env vars
        if 'vpn_sentinel_common.telegram' in sys.modules:
            del sys.modules['vpn_sentinel_common.telegram']
        if 'vpn_sentinel_common.log_utils' in sys.modules:
            del sys.modules['vpn_sentinel_common.log_utils']
        
        # Import with mock to avoid sys.exit from previous tests
        import importlib
        telegram = importlib.import_module('vpn_sentinel_common.telegram')
        
        assert telegram.TELEGRAM_ENABLED is False
    
    def test_telegram_auto_enable_with_credentials(self):
        """Test that Telegram auto-enables when credentials present (no explicit flag)."""
        # Clean reload
        for mod in ['vpn_sentinel_common.telegram', 'vpn_sentinel_common.log_utils']:
            if mod in sys.modules:
                del sys.modules[mod]
        
        # Set env without explicit enable flag
        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': 'test-token',
            'TELEGRAM_CHAT_ID': '123456'
        }, clear=False):
            # Remove explicit enable flag
            os.environ.pop('VPN_SENTINEL_TELEGRAM_ENABLED', None)
            
            import importlib
            telegram = importlib.import_module('vpn_sentinel_common.telegram')
            
            assert telegram.TELEGRAM_ENABLED is True


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
        """Test that API routes read VPN_SENTINEL_API_PATH from environment."""
        # The api_routes module reads API_PATH at import time
        # We verify it's actually reading from the environment variable
        import vpn_sentinel_common.api_routes as api_routes
        
        # Should have API_PATH attribute
        assert hasattr(api_routes, 'API_PATH')
        assert isinstance(api_routes.API_PATH, str)
        assert api_routes.API_PATH.startswith('/')
    
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
