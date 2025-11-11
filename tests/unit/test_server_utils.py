"""Unit tests for vpn_sentinel_common.server_utils module.

Tests server utility functions including Flask app running and port configuration.
"""
import pytest
import ssl
import sys
from unittest.mock import patch, MagicMock, call
from vpn_sentinel_common.server_utils import run_flask_app, get_port_config


class TestGetPortConfig:
    """Tests for get_port_config() function."""

    def test_get_port_config_defaults(self):
        """Test port config returns default values."""
        with patch.dict('os.environ', {}, clear=True):
            config = get_port_config()
            assert config['api_port'] == 5000
            assert config['health_port'] == 8081
            assert config['dashboard_port'] == 8080

    def test_get_port_config_custom(self):
        """Test port config reads from environment variables."""
        with patch.dict('os.environ', {
            'VPN_SENTINEL_SERVER_API_PORT': '6000',
            'VPN_SENTINEL_SERVER_HEALTH_PORT': '7081',
            'VPN_SENTINEL_SERVER_DASHBOARD_PORT': '7080'
        }):
            config = get_port_config()
            assert config['api_port'] == 6000
            assert config['health_port'] == 7081
            assert config['dashboard_port'] == 7080

    def test_get_port_config_partial_override(self):
        """Test port config with only some values overridden."""
        with patch.dict('os.environ', {
            'VPN_SENTINEL_SERVER_API_PORT': '9999'
        }, clear=True):
            config = get_port_config()
            assert config['api_port'] == 9999
            assert config['health_port'] == 8081  # Default
            assert config['dashboard_port'] == 8080  # Default

    def test_get_port_config_returns_dict(self):
        """Test port config returns a dictionary with expected keys."""
        config = get_port_config()
        assert isinstance(config, dict)
        assert 'api_port' in config
        assert 'health_port' in config
        assert 'dashboard_port' in config

    def test_get_port_config_returns_integers(self):
        """Test port config values are integers."""
        with patch.dict('os.environ', {
            'VPN_SENTINEL_SERVER_API_PORT': '5555',
            'VPN_SENTINEL_SERVER_HEALTH_PORT': '6666',
            'VPN_SENTINEL_SERVER_DASHBOARD_PORT': '7777'
        }):
            config = get_port_config()
            assert isinstance(config['api_port'], int)
            assert isinstance(config['health_port'], int)
            assert isinstance(config['dashboard_port'], int)


class TestRunFlaskApp:
    """Tests for run_flask_app() function."""

    def test_run_flask_app_without_tls(self):
        """Test running Flask app without TLS."""
        mock_app = MagicMock()
        mock_server = MagicMock()
        
        with patch.dict('os.environ', {}, clear=True):
            with patch('vpn_sentinel_common.server_utils.make_server', return_value=mock_server) as mock_make:
                with patch('vpn_sentinel_common.server_utils.log_info') as mock_log:
                    run_flask_app(mock_app, 5000, 'Test API')
                    
                    # Verify make_server called without SSL context
                    mock_make.assert_called_once_with(
                        '0.0.0.0', 5000, mock_app, threaded=True
                    )
                    
                    # Verify server started
                    mock_server.serve_forever.assert_called_once()
                    
                    # Verify log message
                    mock_log.assert_called_once_with('server', '🌐 Starting Test API on 0.0.0.0:5000')

    def test_run_flask_app_with_tls(self):
        """Test running Flask app with TLS enabled."""
        mock_app = MagicMock()
        mock_server = MagicMock()
        mock_ssl_context = MagicMock()
        
        with patch.dict('os.environ', {
            'VPN_SENTINEL_TLS_CERT_PATH': '/path/to/cert.pem',
            'VPN_SENTINEL_TLS_KEY_PATH': '/path/to/key.pem'
        }):
            with patch('vpn_sentinel_common.server_utils.ssl.SSLContext', return_value=mock_ssl_context) as mock_ssl:
                with patch('vpn_sentinel_common.server_utils.make_server', return_value=mock_server) as mock_make:
                    with patch('vpn_sentinel_common.server_utils.log_info') as mock_log:
                        run_flask_app(mock_app, 5000, 'Test API')
                        
                        # Verify SSL context created
                        mock_ssl.assert_called_once_with(ssl.PROTOCOL_TLS_SERVER)
                        
                        # Verify certificate loaded
                        mock_ssl_context.load_cert_chain.assert_called_once_with(
                            '/path/to/cert.pem', '/path/to/key.pem'
                        )
                        
                        # Verify make_server called with SSL context
                        mock_make.assert_called_once_with(
                            '0.0.0.0', 5000, mock_app, threaded=True, ssl_context=mock_ssl_context
                        )
                        
                        # Verify server started
                        mock_server.serve_forever.assert_called_once()
                        
                        # Verify TLS log message
                        mock_log.assert_called_once_with('server', '🔒 Starting Test API on 0.0.0.0:5000 with TLS')

    def test_run_flask_app_custom_host(self):
        """Test running Flask app on custom host."""
        mock_app = MagicMock()
        mock_server = MagicMock()
        
        with patch.dict('os.environ', {}, clear=True):
            with patch('vpn_sentinel_common.server_utils.make_server', return_value=mock_server) as mock_make:
                with patch('vpn_sentinel_common.server_utils.log_info'):
                    run_flask_app(mock_app, 8080, 'Dashboard', host='127.0.0.1')
                    
                    # Verify host override
                    mock_make.assert_called_once_with(
                        '127.0.0.1', 8080, mock_app, threaded=True
                    )

    def test_run_flask_app_exception_exits(self):
        """Test Flask app exits on exception."""
        mock_app = MagicMock()
        
        with patch.dict('os.environ', {}, clear=True):
            with patch('vpn_sentinel_common.server_utils.make_server', side_effect=Exception('Port in use')):
                with patch('vpn_sentinel_common.server_utils.log_info') as mock_log:
                    with pytest.raises(SystemExit) as exc_info:
                        run_flask_app(mock_app, 5000, 'Test API')
                    
                    # Verify exit code
                    assert exc_info.value.code == 1
                    
                    # Verify error logged
                    assert mock_log.call_count == 1
                    error_call = mock_log.call_args_list[0]
                    assert 'Error starting Test API' in error_call[0][1]
                    assert 'Port in use' in error_call[0][1]

    def test_run_flask_app_tls_cert_only_no_ssl(self):
        """Test TLS not enabled with only cert path (missing key)."""
        mock_app = MagicMock()
        mock_server = MagicMock()
        
        with patch.dict('os.environ', {'VPN_SENTINEL_TLS_CERT_PATH': '/cert.pem'}):
            with patch('vpn_sentinel_common.server_utils.make_server', return_value=mock_server) as mock_make:
                with patch('vpn_sentinel_common.server_utils.log_info') as mock_log:
                    run_flask_app(mock_app, 5000, 'Test API')
                    
                    # Should NOT use SSL (missing key)
                    mock_make.assert_called_once_with(
                        '0.0.0.0', 5000, mock_app, threaded=True
                    )
                    
                    # Should log non-TLS message
                    mock_log.assert_called_once_with('server', '🌐 Starting Test API on 0.0.0.0:5000')

    def test_run_flask_app_tls_key_only_no_ssl(self):
        """Test TLS not enabled with only key path (missing cert)."""
        mock_app = MagicMock()
        mock_server = MagicMock()
        
        with patch.dict('os.environ', {'VPN_SENTINEL_TLS_KEY_PATH': '/key.pem'}):
            with patch('vpn_sentinel_common.server_utils.make_server', return_value=mock_server) as mock_make:
                with patch('vpn_sentinel_common.server_utils.log_info') as mock_log:
                    run_flask_app(mock_app, 5000, 'Test API')
                    
                    # Should NOT use SSL (missing cert)
                    mock_make.assert_called_once_with(
                        '0.0.0.0', 5000, mock_app, threaded=True
                    )
                    
                    # Should log non-TLS message
                    mock_log.assert_called_once_with('server', '🌐 Starting Test API on 0.0.0.0:5000')

    def test_run_flask_app_threaded_enabled(self):
        """Test Flask app runs with threading enabled."""
        mock_app = MagicMock()
        mock_server = MagicMock()
        
        with patch.dict('os.environ', {}, clear=True):
            with patch('vpn_sentinel_common.server_utils.make_server', return_value=mock_server) as mock_make:
                with patch('vpn_sentinel_common.server_utils.log_info'):
                    run_flask_app(mock_app, 5000, 'Test API')
                    
                    # Verify threaded=True
                    call_kwargs = mock_make.call_args[1]
                    assert call_kwargs['threaded'] is True

    def test_run_flask_app_ssl_load_error_exits(self):
        """Test Flask app exits on SSL certificate loading error."""
        mock_app = MagicMock()
        mock_ssl_context = MagicMock()
        mock_ssl_context.load_cert_chain.side_effect = FileNotFoundError('Cert not found')
        
        with patch.dict('os.environ', {
            'VPN_SENTINEL_TLS_CERT_PATH': '/invalid/cert.pem',
            'VPN_SENTINEL_TLS_KEY_PATH': '/invalid/key.pem'
        }):
            with patch('vpn_sentinel_common.server_utils.ssl.SSLContext', return_value=mock_ssl_context):
                with patch('vpn_sentinel_common.server_utils.log_info') as mock_log:
                    with pytest.raises(SystemExit) as exc_info:
                        run_flask_app(mock_app, 5000, 'Test API')
                    
                    # Verify exit code
                    assert exc_info.value.code == 1
                    
                    # Verify error logged
                    error_logged = any('Error starting' in str(call) for call in mock_log.call_args_list)
                    assert error_logged


class TestServerUtilsIntegration:
    """Integration tests for server_utils module."""

    def test_port_config_and_run_integration(self):
        """Test port config can be used to run Flask apps."""
        mock_app = MagicMock()
        mock_server = MagicMock()
        
        with patch.dict('os.environ', {
            'VPN_SENTINEL_SERVER_API_PORT': '5555'
        }, clear=True):
            config = get_port_config()
            
            with patch('vpn_sentinel_common.server_utils.make_server', return_value=mock_server):
                with patch('vpn_sentinel_common.server_utils.log_info'):
                    run_flask_app(mock_app, config['api_port'], 'API')
                    
                    # Verify correct port used
                    assert mock_server.serve_forever.called
