"""Unit tests for vpn_sentinel_common.telegram_commands module.

Tests Telegram bot command handlers.
"""
import pytest
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, Mock, MagicMock, call
from vpn_sentinel_common import telegram_commands


class TestFormatTimeAgo:
    """Tests for format_time_ago() function."""

    def test_format_time_ago_just_now(self):
        """Test formatting time less than 1 minute ago."""
        now = datetime.now(timezone.utc)
        iso_string = now.isoformat()
        
        result = telegram_commands.format_time_ago(iso_string)
        
        assert result == "just now"

    def test_format_time_ago_one_minute(self):
        """Test formatting exactly 1 minute ago."""
        time = datetime.now(timezone.utc) - timedelta(minutes=1)
        iso_string = time.isoformat()
        
        result = telegram_commands.format_time_ago(iso_string)
        
        assert result == "1 minute ago"

    def test_format_time_ago_multiple_minutes(self):
        """Test formatting multiple minutes ago."""
        time = datetime.now(timezone.utc) - timedelta(minutes=5)
        iso_string = time.isoformat()
        
        result = telegram_commands.format_time_ago(iso_string)
        
        assert result == "5 minutes ago"

    def test_format_time_ago_one_hour(self):
        """Test formatting exactly 1 hour ago."""
        time = datetime.now(timezone.utc) - timedelta(hours=1)
        iso_string = time.isoformat()
        
        result = telegram_commands.format_time_ago(iso_string)
        
        assert result == "1 hour ago"

    def test_format_time_ago_multiple_hours(self):
        """Test formatting multiple hours ago."""
        time = datetime.now(timezone.utc) - timedelta(hours=3)
        iso_string = time.isoformat()
        
        result = telegram_commands.format_time_ago(iso_string)
        
        assert result == "3 hours ago"

    def test_format_time_ago_invalid_format(self):
        """Test handling invalid time format."""
        result = telegram_commands.format_time_ago("invalid-time")
        
        assert result == "unknown"

    def test_format_time_ago_empty_string(self):
        """Test handling empty string."""
        result = telegram_commands.format_time_ago("")
        
        assert result == "unknown"

    def test_format_time_ago_59_minutes(self):
        """Test formatting 59 minutes (boundary case)."""
        time = datetime.now(timezone.utc) - timedelta(minutes=59)
        iso_string = time.isoformat()
        
        result = telegram_commands.format_time_ago(iso_string)
        
        assert result == "59 minutes ago"

    def test_format_time_ago_60_minutes(self):
        """Test formatting 60 minutes (should be 1 hour)."""
        time = datetime.now(timezone.utc) - timedelta(minutes=60)
        iso_string = time.isoformat()
        
        result = telegram_commands.format_time_ago(iso_string)
        
        assert result == "1 hour ago"


class TestHandlePing:
    """Tests for handle_ping() function."""

    @patch('vpn_sentinel_common.telegram_commands.telegram.send_telegram_message')
    def test_handle_ping_with_no_clients(self, mock_send):
        """Test /ping command with no active clients."""
        # Mock the client_status dict that gets imported locally
        mock_api_routes = Mock()
        mock_api_routes.client_status = {}
        
        with patch.dict('sys.modules', {'vpn_sentinel_common.api_routes': mock_api_routes}):
            telegram_commands.handle_ping('123456', '/ping')
            
            mock_send.assert_called_once()
            message = mock_send.call_args[0][0]
            assert '🏓' in message
            assert 'Pong!' in message
            assert 'Active clients: 0' in message

    @patch('vpn_sentinel_common.telegram_commands.telegram.send_telegram_message')
    def test_handle_ping_with_clients(self, mock_send):
        """Test /ping command with active clients."""
        mock_api_routes = Mock()
        mock_api_routes.client_status = {
            'client-1': {'ip': '1.2.3.4'},
            'client-2': {'ip': '5.6.7.8'}
        }
        
        with patch.dict('sys.modules', {'vpn_sentinel_common.api_routes': mock_api_routes}):
            telegram_commands.handle_ping('123456', '/ping')
            
            message = mock_send.call_args[0][0]
            assert 'Active clients: 2' in message

    @patch('vpn_sentinel_common.telegram_commands.telegram.send_telegram_message')
    def test_handle_ping_includes_server_time(self, mock_send):
        """Test /ping includes server time."""
        mock_api_routes = Mock()
        mock_api_routes.client_status = {}
        
        with patch.dict('sys.modules', {'vpn_sentinel_common.api_routes': mock_api_routes}):
            telegram_commands.handle_ping('123456', '/ping')
            
            message = mock_send.call_args[0][0]
            assert 'Server time:' in message
            assert 'UTC' in message

    @patch('vpn_sentinel_common.telegram_commands.telegram.send_telegram_message')
    def test_handle_ping_includes_thresholds(self, mock_send):
        """Test /ping includes monitoring thresholds."""
        mock_api_routes = Mock()
        mock_api_routes.client_status = {}
        
        with patch.dict('sys.modules', {'vpn_sentinel_common.api_routes': mock_api_routes}):
            telegram_commands.handle_ping('123456', '/ping')
            
            message = mock_send.call_args[0][0]
            assert 'Alert threshold:' in message
            assert 'Check interval:' in message


class TestHandleStatus:
    """Tests for handle_status() function."""

    @patch('vpn_sentinel_common.telegram_commands.telegram.send_telegram_message')
    def test_handle_status_no_clients(self, mock_send):
        """Test /status command with no active clients."""
        mock_api_routes = Mock()
        mock_api_routes.client_status = {}
        
        with patch.dict('sys.modules', {'vpn_sentinel_common.api_routes': mock_api_routes}):
            telegram_commands.handle_status('123456', '/status')
            
            message = mock_send.call_args[0][0]
            assert '📊' in message
            assert 'VPN Status' in message
            assert 'No active VPN clients' in message

    @patch('vpn_sentinel_common.telegram_commands.telegram.send_telegram_message')
    def test_handle_status_with_single_client(self, mock_send):
        """Test /status command with one client."""
        mock_api_routes = Mock()
        mock_api_routes.client_status = {
            'office-vpn': {
                'ip': '203.0.113.1',
                'location': 'US',
                'last_seen': datetime.now(timezone.utc).isoformat()
            }
        }
        
        with patch.dict('sys.modules', {'vpn_sentinel_common.api_routes': mock_api_routes}):
            telegram_commands.handle_status('123456', '/status')
            
            message = mock_send.call_args[0][0]
            assert 'office-vpn' in message
            assert '203.0.113.1' in message
            assert 'US' in message
            assert '🟢' in message

    @patch('vpn_sentinel_common.telegram_commands.telegram.send_telegram_message')
    def test_handle_status_with_multiple_clients(self, mock_send):
        """Test /status command with multiple clients."""
        mock_api_routes = Mock()
        mock_api_routes.client_status = {
            'client-1': {
                'ip': '1.2.3.4',
                'location': 'UK',
                'last_seen': datetime.now(timezone.utc).isoformat()
            },
            'client-2': {
                'ip': '5.6.7.8',
                'location': 'FR',
                'last_seen': (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
            }
        }
        
        with patch.dict('sys.modules', {'vpn_sentinel_common.api_routes': mock_api_routes}):
            telegram_commands.handle_status('123456', '/status')
            
            message = mock_send.call_args[0][0]
            assert 'client-1' in message
            assert 'client-2' in message
            assert '1.2.3.4' in message
            assert '5.6.7.8' in message

    @patch('vpn_sentinel_common.telegram_commands.telegram.send_telegram_message')
    def test_handle_status_formats_time_ago(self, mock_send):
        """Test /status formats last_seen as time ago."""
        old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        mock_api_routes = Mock()
        mock_api_routes.client_status = {
            'test-client': {
                'ip': '1.2.3.4',
                'location': 'US',
                'last_seen': old_time.isoformat()
            }
        }
        
        with patch.dict('sys.modules', {'vpn_sentinel_common.api_routes': mock_api_routes}):
            telegram_commands.handle_status('123456', '/status')
            
            message = mock_send.call_args[0][0]
            assert '10 minutes ago' in message

    @patch('vpn_sentinel_common.telegram_commands.telegram.send_telegram_message')
    def test_handle_status_handles_missing_fields(self, mock_send):
        """Test /status handles missing client info fields."""
        mock_api_routes = Mock()
        mock_api_routes.client_status = {
            'incomplete-client': {}
        }
        
        with patch.dict('sys.modules', {'vpn_sentinel_common.api_routes': mock_api_routes}):
            telegram_commands.handle_status('123456', '/status')
            
            message = mock_send.call_args[0][0]
            assert 'incomplete-client' in message
            assert 'unknown' in message

    @patch('vpn_sentinel_common.telegram_commands.telegram.send_telegram_message')
    def test_handle_status_includes_server_time(self, mock_send):
        """Test /status includes server time."""
        mock_api_routes = Mock()
        mock_api_routes.client_status = {}
        
        with patch.dict('sys.modules', {'vpn_sentinel_common.api_routes': mock_api_routes}):
            telegram_commands.handle_status('123456', '/status')
            
            message = mock_send.call_args[0][0]
            assert 'Server time:' in message
            assert 'UTC' in message


class TestHandleHelp:
    """Tests for handle_help() function."""

    def test_handle_help_sends_message(self):
        """Test /help command sends help message."""
        with patch('vpn_sentinel_common.telegram_commands.telegram.send_telegram_message') as mock_send:
            telegram_commands.handle_help('123456', '/help')
            
            mock_send.assert_called_once()

    def test_handle_help_includes_all_commands(self):
        """Test /help includes all available commands."""
        with patch('vpn_sentinel_common.telegram_commands.telegram.send_telegram_message') as mock_send:
            telegram_commands.handle_help('123456', '/help')
            
            message = mock_send.call_args[0][0]
            assert '/ping' in message
            assert '/status' in message
            assert '/help' in message

    def test_handle_help_describes_functionality(self):
        """Test /help describes bot functionality."""
        with patch('vpn_sentinel_common.telegram_commands.telegram.send_telegram_message') as mock_send:
            telegram_commands.handle_help('123456', '/help')
            
            message = mock_send.call_args[0][0]
            assert 'VPN Sentinel' in message
            assert 'monitor' in message.lower()
            assert 'Automatic Notifications' in message

    def test_handle_help_includes_emojis(self):
        """Test /help includes visual emojis."""
        with patch('vpn_sentinel_common.telegram_commands.telegram.send_telegram_message') as mock_send:
            telegram_commands.handle_help('123456', '/help')
            
            message = mock_send.call_args[0][0]
            assert '❓' in message
            assert '🏓' in message
            assert '📊' in message


class TestRegisterAllCommands:
    """Tests for register_all_commands() function."""

    def test_register_all_commands_registers_ping(self):
        """Test register_all_commands registers ping handler."""
        with patch('vpn_sentinel_common.telegram_commands.telegram.register_command') as mock_register:
            with patch('vpn_sentinel_common.telegram_commands.log_info'):
                telegram_commands.register_all_commands()
                
                # Check if ping was registered
                ping_calls = [c for c in mock_register.call_args_list if c[0][0] == 'ping']
                assert len(ping_calls) == 1
                assert ping_calls[0][0][1] == telegram_commands.handle_ping

    def test_register_all_commands_registers_status(self):
        """Test register_all_commands registers status handler."""
        with patch('vpn_sentinel_common.telegram_commands.telegram.register_command') as mock_register:
            with patch('vpn_sentinel_common.telegram_commands.log_info'):
                telegram_commands.register_all_commands()
                
                # Check if status was registered
                status_calls = [c for c in mock_register.call_args_list if c[0][0] == 'status']
                assert len(status_calls) == 1
                assert status_calls[0][0][1] == telegram_commands.handle_status

    def test_register_all_commands_registers_help(self):
        """Test register_all_commands registers help handler."""
        with patch('vpn_sentinel_common.telegram_commands.telegram.register_command') as mock_register:
            with patch('vpn_sentinel_common.telegram_commands.log_info'):
                telegram_commands.register_all_commands()
                
                # Check if help was registered
                help_calls = [c for c in mock_register.call_args_list if c[0][0] == 'help']
                assert len(help_calls) == 1
                assert help_calls[0][0][1] == telegram_commands.handle_help

    def test_register_all_commands_logs_success(self):
        """Test register_all_commands logs success message."""
        with patch('vpn_sentinel_common.telegram_commands.telegram.register_command'):
            with patch('vpn_sentinel_common.telegram_commands.log_info') as mock_log:
                telegram_commands.register_all_commands()
                
                mock_log.assert_called_once()
                call_args = mock_log.call_args[0]
                assert call_args[0] == 'telegram'
                assert 'Registered' in call_args[1]

    def test_register_all_commands_registers_all_three(self):
        """Test register_all_commands registers exactly 3 commands."""
        with patch('vpn_sentinel_common.telegram_commands.telegram.register_command') as mock_register:
            with patch('vpn_sentinel_common.telegram_commands.log_info'):
                telegram_commands.register_all_commands()
                
                assert mock_register.call_count == 3


class TestTelegramCommandsIntegration:
    """Integration tests for telegram_commands module."""

    def test_all_handlers_callable(self):
        """Test all command handlers are callable."""
        assert callable(telegram_commands.handle_ping)
        assert callable(telegram_commands.handle_status)
        assert callable(telegram_commands.handle_help)

    def test_format_time_ago_callable(self):
        """Test format_time_ago is callable."""
        assert callable(telegram_commands.format_time_ago)

    def test_register_all_commands_callable(self):
        """Test register_all_commands is callable."""
        assert callable(telegram_commands.register_all_commands)

    @patch('vpn_sentinel_common.telegram_commands.telegram.send_telegram_message')
    def test_handlers_accept_correct_arguments(self, mock_send):
        """Test handlers accept chat_id and message_text."""
        mock_api_routes = Mock()
        mock_api_routes.client_status = {}
        
        with patch.dict('sys.modules', {'vpn_sentinel_common.api_routes': mock_api_routes}):
            # Should not raise TypeError
            telegram_commands.handle_ping('123', 'test')
            telegram_commands.handle_status('123', 'test')
            telegram_commands.handle_help('123', 'test')
