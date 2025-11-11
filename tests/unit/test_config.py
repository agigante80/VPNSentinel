"""Unit tests for vpn_sentinel_common.config module.

Tests configuration loading and client ID generation.
"""
import pytest
import time
from unittest.mock import patch
from vpn_sentinel_common.config import (
    _sanitize_client_id,
    generate_client_id,
    load_config
)


class TestSanitizeClientId:
    """Tests for _sanitize_client_id() function."""

    def test_sanitize_client_id_lowercase(self):
        """Test client ID is converted to lowercase."""
        result = _sanitize_client_id('TEST-CLIENT')
        assert result == 'test-client'

    def test_sanitize_client_id_replaces_invalid_chars(self):
        """Test invalid characters are replaced with hyphens."""
        result = _sanitize_client_id('test@client#123')
        assert result == 'test-client-123'

    def test_sanitize_client_id_removes_consecutive_hyphens(self):
        """Test consecutive hyphens are collapsed."""
        result = _sanitize_client_id('test---client')
        assert result == 'test-client'

    def test_sanitize_client_id_strips_leading_trailing_hyphens(self):
        """Test leading and trailing hyphens are removed."""
        result = _sanitize_client_id('-test-client-')
        assert result == 'test-client'

    def test_sanitize_client_id_empty_returns_default(self):
        """Test empty string returns default."""
        result = _sanitize_client_id('')
        assert result == 'sanitized-client'

    def test_sanitize_client_id_only_invalid_chars(self):
        """Test string with only invalid chars returns default."""
        result = _sanitize_client_id('@@@@')
        assert result == 'sanitized-client'

    def test_sanitize_client_id_spaces_to_hyphens(self):
        """Test spaces are converted to hyphens."""
        result = _sanitize_client_id('test client 123')
        assert result == 'test-client-123'

    def test_sanitize_client_id_alphanumeric_preserved(self):
        """Test alphanumeric characters are preserved."""
        result = _sanitize_client_id('test123client456')
        assert result == 'test123client456'


class TestGenerateClientId:
    """Tests for generate_client_id() function."""

    def test_generate_client_id_from_env(self):
        """Test client ID is read from environment."""
        env = {'VPN_SENTINEL_CLIENT_ID': 'office-vpn'}
        result = generate_client_id(env)
        assert result == 'office-vpn'

    def test_generate_client_id_sanitizes_invalid(self):
        """Test client ID is sanitized if contains invalid characters."""
        env = {'VPN_SENTINEL_CLIENT_ID': 'Office VPN #1'}
        result = generate_client_id(env)
        assert result == 'office-vpn-1'

    def test_generate_client_id_no_sanitize_if_valid(self):
        """Test valid client ID is not sanitized."""
        env = {'VPN_SENTINEL_CLIENT_ID': 'office-vpn-123'}
        result = generate_client_id(env)
        assert result == 'office-vpn-123'

    def test_generate_client_id_uppercase_sanitized(self):
        """Test uppercase letters trigger sanitization."""
        env = {'VPN_SENTINEL_CLIENT_ID': 'Office-VPN'}
        result = generate_client_id(env)
        assert result == 'office-vpn'

    def test_generate_client_id_auto_generated(self):
        """Test client ID is auto-generated when not in env."""
        with patch('vpn_sentinel_common.config.time.time', return_value=1699721234.567):
            with patch('vpn_sentinel_common.config.random.randint', return_value=123456):
                env = {}
                result = generate_client_id(env)
                # timestamp_part = last 7 digits of 1699721234 = 9721234
                assert result == 'vpn-client-9721234123456'

    def test_generate_client_id_different_timestamps(self):
        """Test different timestamps produce different IDs."""
        with patch('vpn_sentinel_common.config.time.time', return_value=1699721234.0):
            with patch('vpn_sentinel_common.config.random.randint', return_value=111111):
                result1 = generate_client_id({})
                # Last 7 digits of 1699721234 = 9721234
        
        with patch('vpn_sentinel_common.config.time.time', return_value=1799721234.0):
            with patch('vpn_sentinel_common.config.random.randint', return_value=111111):
                result2 = generate_client_id({})
                # Last 7 digits of 1799721234 = 9721234 (wait, same!)
        
        # Let's use a significantly different timestamp
        with patch('vpn_sentinel_common.config.time.time', return_value=1600000000.0):
            with patch('vpn_sentinel_common.config.random.randint', return_value=111111):
                result3 = generate_client_id({})
                # Last 7 digits of 1600000000 = 0000000
        
        assert result1 != result3

    def test_generate_client_id_random_component(self):
        """Test random component makes IDs unique."""
        with patch('vpn_sentinel_common.config.time.time', return_value=1699721234.567):
            with patch('vpn_sentinel_common.config.random.randint', side_effect=[111111, 222222]):
                result1 = generate_client_id({})
                result2 = generate_client_id({})
            
            assert result1 != result2
            assert result1.startswith('vpn-client-')
            assert result2.startswith('vpn-client-')

    def test_generate_client_id_empty_string_auto_generates(self):
        """Test empty string in env triggers auto-generation."""
        with patch('vpn_sentinel_common.config.time.time', return_value=1699721234.567):
            with patch('vpn_sentinel_common.config.random.randint', return_value=999999):
                env = {'VPN_SENTINEL_CLIENT_ID': ''}
                result = generate_client_id(env)
                # Empty string is falsy, should auto-generate
                assert result.startswith('vpn-client-')


class TestLoadConfig:
    """Tests for load_config() function."""

    def test_load_config_defaults(self):
        """Test config loads with default values."""
        config = load_config({})
        
        assert config['version'] == '1.0.0-dev'
        assert config['api_base'] == 'http://your-server-url:5000'
        assert config['api_path'] == '/api/v1'
        assert config['server_url'] == 'http://your-server-url:5000/api/v1'
        assert config['is_https'] is False
        assert config['timeout'] == 30
        assert config['interval'] == 300
        assert config['client_id'].startswith('vpn-client-')
        assert config['tls_cert_path'] == ''
        assert config['allow_insecure'] is False
        assert config['debug'] is False

    def test_load_config_custom_values(self):
        """Test config loads custom environment values."""
        env = {
            'VERSION': '2.5.0',
            'VPN_SENTINEL_URL': 'https://vpn.example.com:8443',
            'VPN_SENTINEL_API_PATH': '/custom/api',
            'VPN_SENTINEL_TIMEOUT': '60',
            'VPN_SENTINEL_INTERVAL': '600',
            'VPN_SENTINEL_CLIENT_ID': 'test-client',
            'VPN_SENTINEL_TLS_CERT_PATH': '/certs/ca.pem',
            'VPN_SENTINEL_ALLOW_INSECURE': 'true',
            'VPN_SENTINEL_DEBUG': 'true'
        }
        config = load_config(env)
        
        assert config['version'] == '2.5.0'
        assert config['api_base'] == 'https://vpn.example.com:8443'
        assert config['api_path'] == '/custom/api'
        assert config['server_url'] == 'https://vpn.example.com:8443/custom/api'
        assert config['is_https'] is True
        assert config['timeout'] == 60
        assert config['interval'] == 600
        assert config['client_id'] == 'test-client'
        assert config['tls_cert_path'] == '/certs/ca.pem'
        assert config['allow_insecure'] is True
        assert config['debug'] is True

    def test_load_config_version_from_commit(self):
        """Test version is generated from commit hash."""
        env = {'COMMIT_HASH': 'abc123def456'}
        config = load_config(env)
        
        assert config['version'] == '1.0.0-dev-abc123def456'

    def test_load_config_api_path_adds_leading_slash(self):
        """Test API path gets leading slash if missing."""
        env = {'VPN_SENTINEL_API_PATH': 'api/v1'}
        config = load_config(env)
        
        assert config['api_path'] == '/api/v1'

    def test_load_config_api_path_empty_uses_default(self):
        """Test empty API path uses default."""
        env = {'VPN_SENTINEL_API_PATH': ''}
        config = load_config(env)
        
        assert config['api_path'] == '/api/v1'

    def test_load_config_https_detection(self):
        """Test HTTPS is detected from URL."""
        env_https = {'VPN_SENTINEL_URL': 'https://example.com'}
        config_https = load_config(env_https)
        assert config_https['is_https'] is True
        
        env_http = {'VPN_SENTINEL_URL': 'http://example.com'}
        config_http = load_config(env_http)
        assert config_http['is_https'] is False

    def test_load_config_timeout_invalid_uses_default(self):
        """Test invalid timeout value uses default."""
        env = {'VPN_SENTINEL_TIMEOUT': 'invalid'}
        config = load_config(env)
        
        assert config['timeout'] == 30

    def test_load_config_interval_invalid_uses_default(self):
        """Test invalid interval value uses default."""
        env = {'VPN_SENTINEL_INTERVAL': 'not-a-number'}
        config = load_config(env)
        
        assert config['interval'] == 300

    def test_load_config_timeout_legacy_env(self):
        """Test legacy TIMEOUT env var is supported."""
        env = {'TIMEOUT': '45'}
        config = load_config(env)
        
        assert config['timeout'] == 45

    def test_load_config_interval_legacy_env(self):
        """Test legacy INTERVAL env var is supported."""
        env = {'INTERVAL': '450'}
        config = load_config(env)
        
        assert config['interval'] == 450

    def test_load_config_new_env_overrides_legacy(self):
        """Test new env vars override legacy ones."""
        env = {
            'TIMEOUT': '45',
            'VPN_SENTINEL_TIMEOUT': '60',
            'INTERVAL': '450',
            'VPN_SENTINEL_INTERVAL': '600'
        }
        config = load_config(env)
        
        assert config['timeout'] == 60
        assert config['interval'] == 600

    def test_load_config_allow_insecure_case_insensitive(self):
        """Test allow_insecure parsing is case-insensitive."""
        test_cases = [
            ('true', True),
            ('True', True),
            ('TRUE', True),
            ('false', False),
            ('False', False),
            ('FALSE', False),
            ('yes', False),  # Only 'true' should set it to True
            ('1', False)
        ]
        
        for value, expected in test_cases:
            env = {'VPN_SENTINEL_ALLOW_INSECURE': value}
            config = load_config(env)
            assert config['allow_insecure'] == expected, f"Failed for value: {value}"

    def test_load_config_debug_case_insensitive(self):
        """Test debug parsing is case-insensitive."""
        test_cases = [
            ('true', True),
            ('True', True),
            ('TRUE', True),
            ('false', False),
            ('anything-else', False)
        ]
        
        for value, expected in test_cases:
            env = {'VPN_SENTINEL_DEBUG': value}
            config = load_config(env)
            assert config['debug'] == expected, f"Failed for value: {value}"

    def test_load_config_returns_dict(self):
        """Test load_config returns a dictionary."""
        config = load_config({})
        
        assert isinstance(config, dict)
        assert 'version' in config
        assert 'server_url' in config
        assert 'client_id' in config

    def test_load_config_timeout_zero(self):
        """Test timeout can be set to zero."""
        env = {'VPN_SENTINEL_TIMEOUT': '0'}
        config = load_config(env)
        
        assert config['timeout'] == 0

    def test_load_config_server_url_construction(self):
        """Test server URL is correctly constructed from base and path."""
        test_cases = [
            ('http://example.com', '/api/v1', 'http://example.com/api/v1'),
            ('https://example.com:8443', '/custom', 'https://example.com:8443/custom'),
            ('http://192.168.1.1:5000', '/api/v2', 'http://192.168.1.1:5000/api/v2')
        ]
        
        for base, path, expected_url in test_cases:
            env = {
                'VPN_SENTINEL_URL': base,
                'VPN_SENTINEL_API_PATH': path
            }
            config = load_config(env)
            assert config['server_url'] == expected_url


class TestConfigIntegration:
    """Integration tests for config module."""

    def test_generate_and_load_integration(self):
        """Test client ID generation integrates with config loading."""
        env = {'VPN_SENTINEL_CLIENT_ID': 'test-client'}
        config = load_config(env)
        
        # Generated ID should match
        assert config['client_id'] == generate_client_id(env)

    def test_config_complete_workflow(self):
        """Test complete configuration workflow."""
        with patch('vpn_sentinel_common.config.time.time', return_value=1699721234.567):
            with patch('vpn_sentinel_common.config.random.randint', return_value=123456):
                env = {
                    'VPN_SENTINEL_URL': 'https://vpn.example.com',
                    'VPN_SENTINEL_TIMEOUT': '45'
                }
                config = load_config(env)
                
                # Should have auto-generated client ID
                assert config['client_id'].startswith('vpn-client-')
                # Should respect custom timeout
                assert config['timeout'] == 45
                # Should detect HTTPS
                assert config['is_https'] is True
