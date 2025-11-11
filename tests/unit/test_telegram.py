"""Unit tests for vpn_sentinel_common.telegram module.

Tests Telegram bot integration, message sending, and command handling.
"""
import pytest
from datetime import datetime
from unittest.mock import patch, Mock, MagicMock, call
from vpn_sentinel_common import telegram


class TestSendTelegramMessage:
    """Tests for send_telegram_message function."""

    @patch('vpn_sentinel_common.telegram.TELEGRAM_ENABLED', True)
    @patch('vpn_sentinel_common.telegram.requests.post')
    def test_send_message_success(self, mock_post):
        """Test successful message sending."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = telegram.send_telegram_message("Test message")
        
        assert result is True
        mock_post.assert_called_once()

    @patch('vpn_sentinel_common.telegram.TELEGRAM_ENABLED', False)
    def test_send_message_not_configured(self):
        """Test sending message when Telegram not configured."""
        result = telegram.send_telegram_message("Test")
        
        assert result is False

    @patch('vpn_sentinel_common.telegram.TELEGRAM_ENABLED', True)
    @patch('vpn_sentinel_common.telegram.requests.post')
    def test_send_message_failure(self, mock_post):
        """Test message sending failure."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_post.return_value = mock_response
        
        result = telegram.send_telegram_message("Test")
        
        assert result is False

    @patch('vpn_sentinel_common.telegram.TELEGRAM_ENABLED', True)
    @patch('vpn_sentinel_common.telegram.requests.post')
    def test_send_message_silent(self, mock_post):
        """Test sending silent message."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        telegram.send_telegram_message("Test", silent=True)
        
        call_args = mock_post.call_args
        assert call_args[1]['json']['disable_notification'] is True

    @patch('vpn_sentinel_common.telegram.TELEGRAM_ENABLED', True)
    @patch('vpn_sentinel_common.telegram.requests.post')
    def test_send_message_html_parse_mode(self, mock_post):
        """Test HTML parse mode is used."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        telegram.send_telegram_message("<b>Test</b>")
        
        call_args = mock_post.call_args
        assert call_args[1]['json']['parse_mode'] == "HTML"

    @patch('vpn_sentinel_common.telegram.TELEGRAM_ENABLED', True)
    @patch('vpn_sentinel_common.telegram.requests.post')
    def test_send_message_exception(self, mock_post):
        """Test exception handling during send."""
        mock_post.side_effect = Exception("Network error")
        
        result = telegram.send_telegram_message("Test")
        
        assert result is False


class TestFormatDatetime:
    """Tests for format_datetime function."""

    def test_format_datetime_with_datetime(self):
        """Test formatting specific datetime."""
        dt = datetime(2024, 1, 15, 10, 30, 45)
        result = telegram.format_datetime(dt)
        
        assert result == "2024-01-15 10:30:45 UTC"

    def test_format_datetime_none_uses_current(self):
        """Test formatting None uses current time."""
        result = telegram.format_datetime(None)
        
        # Should be a valid formatted string
        assert "UTC" in result
        assert len(result) == 23  # YYYY-MM-DD HH:MM:SS UTC

    def test_format_datetime_default_arg(self):
        """Test formatting with default argument."""
        result = telegram.format_datetime()
        
        assert "UTC" in result
        assert len(result) == 23


class TestRegisterCommand:
    """Tests for register_command function."""

    def test_register_command_stores_handler(self):
        """Test command handler is stored."""
        def test_handler(chat_id, message_text):
            pass
        
        telegram.register_command("test", test_handler)
        
        # Handler should be stored in _command_handlers
        assert "test" in telegram._command_handlers
        assert telegram._command_handlers["test"] == test_handler


class TestGetUpdates:
    """Tests for get_updates function."""

    @patch('vpn_sentinel_common.telegram.TELEGRAM_ENABLED', False)
    def test_get_updates_not_enabled(self):
        """Test get_updates returns empty when not enabled."""
        updates = telegram.get_updates()
        
        assert updates == []

    @patch('vpn_sentinel_common.telegram.TELEGRAM_ENABLED', True)
    @patch('vpn_sentinel_common.telegram.requests.get')
    def test_get_updates_success(self, mock_get):
        """Test get_updates returns updates."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": True,
            "result": [
                {"update_id": 1, "message": {"text": "test"}}
            ]
        }
        mock_get.return_value = mock_response
        
        updates = telegram.get_updates()
        
        assert len(updates) == 1
        assert updates[0]["update_id"] == 1

    @patch('vpn_sentinel_common.telegram.TELEGRAM_ENABLED', True)
    @patch('vpn_sentinel_common.telegram.requests.get')
    def test_get_updates_failure(self, mock_get):
        """Test get_updates handles failure."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        updates = telegram.get_updates()
        
        assert updates == []

    @patch('vpn_sentinel_common.telegram.TELEGRAM_ENABLED', True)
    @patch('vpn_sentinel_common.telegram.requests.get')
    def test_get_updates_exception(self, mock_get):
        """Test get_updates handles exception."""
        mock_get.side_effect = Exception("Network error")
        
        updates = telegram.get_updates()
        
        assert updates == []


class TestProcessCommand:
    """Tests for process_command function."""

    def test_process_command_with_registered_command(self):
        """Test processing command with registered handler."""
        # Register a test handler
        mock_handler = Mock()
        telegram.register_command("test", mock_handler)
        
        telegram.process_command("12345", "/test argument", 1)
        
        # Handler should be called
        mock_handler.assert_called_once_with("12345", "/test argument")

    def test_process_command_unknown_command(self):
        """Test processing unknown command."""
        # Should not raise exception with unknown command
        telegram.process_command("12345", "/unknown", 1)

    def test_process_command_not_command(self):
        """Test processing regular message (not a command)."""
        # Should not raise exception with non-command text
        telegram.process_command("12345", "regular message", 1)


class TestStartPolling:
    """Tests for start_polling function."""

    @patch('vpn_sentinel_common.telegram.TELEGRAM_ENABLED', False)
    def test_start_polling_not_enabled(self):
        """Test start_polling does nothing when not enabled."""
        telegram.start_polling()
        # Should not raise exception

    @patch('vpn_sentinel_common.telegram.TELEGRAM_ENABLED', True)
    @patch('vpn_sentinel_common.telegram.threading.Thread')
    def test_start_polling_starts_thread(self, mock_thread):
        """Test start_polling starts background thread."""
        telegram.start_polling()
        
        mock_thread.assert_called_once()
        # Thread should be daemon
        call_kwargs = mock_thread.call_args[1]
        assert call_kwargs.get('daemon') is True


class TestNotifications:
    """Test notification functions."""

    @patch('vpn_sentinel_common.telegram.send_telegram_message')
    def test_notify_server_started(self, mock_send):
        """Test server started notification."""
        mock_send.return_value = True
        
        result = telegram.notify_server_started(alert_threshold_min=15, check_interval_min=5)
        
        assert result is True
        mock_send.assert_called_once()
        message = mock_send.call_args[0][0]
        assert "Server Started" in message
        assert "15 minutes" in message

    @patch('vpn_sentinel_common.telegram.send_telegram_message')
    def test_notify_no_clients(self, mock_send):
        """Test no clients notification."""
        mock_send.return_value = True
        
        result = telegram.notify_no_clients()
        
        assert result is True
        message = mock_send.call_args[0][0]
        assert "No VPN Clients" in message or "client" in message.lower()

    @patch('vpn_sentinel_common.telegram.send_telegram_message')
    def test_notify_client_connected(self, mock_send):
        """Test client connected notification."""
        mock_send.return_value = True
        
        result = telegram.notify_client_connected(
            "test-client", "1.2.3.4", "US", "New York", "NY", "United States",
            "ISP Provider", "America/New_York"
        )
        
        assert result is True
        message = mock_send.call_args[0][0]
        assert "test-client" in message
        assert "1.2.3.4" in message

    @patch('vpn_sentinel_common.telegram.send_telegram_message')
    def test_notify_ip_changed(self, mock_send):
        """Test IP changed notification."""
        mock_send.return_value = True
        
        result = telegram.notify_ip_changed(
            "test-client", "1.2.3.4", "5.6.7.8", "London", "England", "UK",
            "ISP Provider", "Europe/London"
        )
        
        assert result is True
        message = mock_send.call_args[0][0]
        assert "test-client" in message
        assert "1.2.3.4" in message
        assert "5.6.7.8" in message


class TestNotificationEdgeCases:
    """Test notification function edge cases and error paths."""

    @patch('vpn_sentinel_common.telegram.send_telegram_message')
    def test_notify_client_connected_with_optional_params(self, mock_send):
        """Test notify_client_connected with optional DNS parameters."""
        mock_send.return_value = True
        
        result = telegram.notify_client_connected(
            "test-client", "1.2.3.4", "US", "City", "Region", "Country",
            "Provider", "UTC", dns_loc="Cloudflare", dns_colo="LAX"
        )
        
        assert result is True

    @patch('vpn_sentinel_common.telegram.send_telegram_message')
    def test_notify_client_connected_send_fails(self, mock_send):
        """Test notify_client_connected when send fails."""
        mock_send.return_value = False
        
        result = telegram.notify_client_connected(
            "test", "1.1.1.1", "US", "City", "Region", "Country",
            "Provider", "UTC"
        )
        
        assert result is False

    @patch('vpn_sentinel_common.telegram.send_telegram_message')
    def test_notify_ip_changed_with_optional_params(self, mock_send):
        """Test notify_ip_changed with optional DNS parameters."""
        mock_send.return_value = True
        
        result = telegram.notify_ip_changed(
            "test", "1.1.1.1", "2.2.2.2", "City", "Region", "Country",
            "Provider", "UTC", dns_loc="Google", dns_colo="NYC", server_ip="3.3.3.3"
        )
        
        assert result is True

    @patch('vpn_sentinel_common.telegram.send_telegram_message')
    def test_notify_ip_changed_send_fails(self, mock_send):
        """Test notify_ip_changed when send fails."""
        mock_send.return_value = False
        
        result = telegram.notify_ip_changed(
            "test", "1.1.1.1", "2.2.2.2", "City", "Region", "Country",
            "Provider", "UTC"
        )
        
        assert result is False

    @patch('vpn_sentinel_common.telegram.send_telegram_message')
    def test_notify_no_clients_send_fails(self, mock_send):
        """Test notify_no_clients when send fails."""
        mock_send.return_value = False
        
        result = telegram.notify_no_clients()
        
        assert result is False

    @patch('vpn_sentinel_common.telegram.send_telegram_message')
    def test_notify_server_started_send_fails(self, mock_send):
        """Test notify_server_started when send fails."""
        mock_send.return_value = False
        
        result = telegram.notify_server_started()
        
        assert result is False

    @patch('vpn_sentinel_common.telegram.send_telegram_message')
    def test_notify_client_connected_full_details(self, mock_send):
        """Test notify_client_connected with all details including DNS."""
        mock_send.return_value = True
        
        result = telegram.notify_client_connected(
            "test-client", "1.2.3.4", "Amsterdam", "Amsterdam", "North Holland", "Netherlands",
            "KPN", "Europe/Amsterdam", dns_loc="Amsterdam", dns_colo="AMS", server_ip="10.0.0.1"
        )
        
        assert result is True
        message = mock_send.call_args[0][0]
        # Check that all details appear in message
        assert "Amsterdam" in message

    @patch('vpn_sentinel_common.telegram.send_telegram_message')
    def test_notify_client_connected_vpn_bypass_detected(self, mock_send):
        """Test notify_client_connected detects VPN bypass (same IP as server)."""
        mock_send.return_value = True
        
        # VPN IP same as server IP = bypass
        result = telegram.notify_client_connected(
            "test-client", "10.0.0.1", "US", "City", "Region", "Country",
            "Provider", "UTC", server_ip="10.0.0.1"
        )
        
        assert result is True
        message = mock_send.call_args[0][0]
        assert "BYPASS" in message or "NOT working" in message

    @patch('vpn_sentinel_common.telegram.send_telegram_message')
    def test_notify_client_connected_vpn_unknown(self, mock_send):
        """Test notify_client_connected with unknown VPN IP."""
        mock_send.return_value = True
        
        result = telegram.notify_client_connected(
            "test-client", "unknown", "US", "City", "Region", "Country",
            "Provider", "UTC"
        )
        
        assert result is True
        message = mock_send.call_args[0][0]
        assert "unknown" in message.lower() or "bypass" in message.lower()

    @patch('vpn_sentinel_common.telegram.send_telegram_message')
    def test_notify_client_connected_dns_leak_detected(self, mock_send):
        """Test notify_client_connected detects DNS leak."""
        mock_send.return_value = True
        
        # DNS location different from country = DNS leak
        result = telegram.notify_client_connected(
            "test-client", "1.2.3.4", "US", "New York", "NY", "United States",
            "Provider", "UTC", dns_loc="Russia", server_ip="10.0.0.1"
        )
        
        assert result is True
        message = mock_send.call_args[0][0]
        assert "leak" in message.lower() or "DNS" in message

    @patch('vpn_sentinel_common.telegram.send_telegram_message')
    def test_notify_client_connected_dns_inconclusive(self, mock_send):
        """Test notify_client_connected with unknown DNS location."""
        mock_send.return_value = True
        
        result = telegram.notify_client_connected(
            "test-client", "1.2.3.4", "US", "City", "Region", "United States",
            "Provider", "UTC", dns_loc="Unknown", server_ip="10.0.0.1"
        )
        
        assert result is True
        message = mock_send.call_args[0][0]
        # Should mention DNS test inconclusive
        assert "inconclusive" in message.lower() or "DNS" in message

    @patch('vpn_sentinel_common.telegram.send_telegram_message')
    def test_notify_client_connected_no_dns_leak(self, mock_send):
        """Test notify_client_connected with no DNS leak (secure connection)."""
        mock_send.return_value = True
        
        # DNS location matches country = no leak
        result = telegram.notify_client_connected(
            "test-client", "1.2.3.4", "US", "New York", "NY", "United States",
            "Provider", "UTC", dns_loc="United States", server_ip="10.0.0.1"
        )
        
        assert result is True
        message = mock_send.call_args[0][0]
        # Should indicate secure connection
        assert "Secure" in message or "No" in message

    @patch('vpn_sentinel_common.telegram.send_telegram_message')
    def test_notify_ip_changed_full_details(self, mock_send):
        """Test notify_ip_changed with all details including DNS."""
        mock_send.return_value = True
        
        result = telegram.notify_ip_changed(
            "test-client", "1.1.1.1", "2.2.2.2", "Berlin", "Berlin", "Germany",
            "Telekom", "Europe/Berlin", dns_loc="Berlin", dns_colo="BER", server_ip="10.0.0.1"
        )
        
        assert result is True
        message = mock_send.call_args[0][0]
        assert "Berlin" in message

    @patch('vpn_sentinel_common.telegram.send_telegram_message')
    def test_notify_ip_changed_with_dns_leak(self, mock_send):
        """Test notify_ip_changed detects DNS leak."""
        mock_send.return_value = True
        
        result = telegram.notify_ip_changed(
            "test-client", "1.1.1.1", "2.2.2.2", "Paris", "Île-de-France", "France",
            "Provider", "Europe/Paris", dns_loc="Germany", server_ip="10.0.0.1"
        )
        
        assert result is True
        message = mock_send.call_args[0][0]
        assert "leak" in message.lower() or "DNS" in message

    @patch('vpn_sentinel_common.telegram.send_telegram_message')
    def test_notify_ip_changed_dns_inconclusive(self, mock_send):
        """Test notify_ip_changed with unknown DNS."""
        mock_send.return_value = True
        
        result = telegram.notify_ip_changed(
            "test-client", "1.1.1.1", "2.2.2.2", "City", "Region", "Country",
            "Provider", "UTC", dns_loc="Unknown", server_ip="10.0.0.1"
        )
        
        assert result is True

    @patch('vpn_sentinel_common.telegram.send_telegram_message')
    def test_notify_ip_changed_no_dns_leak(self, mock_send):
        """Test notify_ip_changed with no DNS leak."""
        mock_send.return_value = True
        
        result = telegram.notify_ip_changed(
            "test-client", "1.1.1.1", "2.2.2.2", "Paris", "Île-de-France", "France",
            "Provider", "Europe/Paris", dns_loc="France", server_ip="10.0.0.1"
        )
        
        assert result is True
        message = mock_send.call_args[0][0]
        assert "Secure" in message or "No" in message


class TestGetUpdatesEdgeCases:
    """Test get_updates edge cases."""

    @patch('vpn_sentinel_common.telegram.TELEGRAM_ENABLED', True)
    @patch('vpn_sentinel_common.telegram.requests.get')
    def test_get_updates_with_offset(self, mock_get):
        """Test get_updates uses offset parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "result": []}
        mock_get.return_value = mock_response
        
        telegram.get_updates(offset=100)
        
        # Check that get was called (offset is in params)
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs.get('params', {}).get('offset') == 100

    @patch('vpn_sentinel_common.telegram.TELEGRAM_ENABLED', True)
    @patch('vpn_sentinel_common.telegram.requests.get')
    def test_get_updates_not_ok_response(self, mock_get):
        """Test get_updates handles non-ok API response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": False, "description": "Error"}
        mock_get.return_value = mock_response
        
        updates = telegram.get_updates()
        
        assert updates == []


class TestProcessCommandEdgeCases:
    """Test process_command edge cases."""

    def test_process_command_with_empty_message(self):
        """Test process_command with empty message."""
        # Should not crash
        telegram.process_command("12345", "", 1)

    def test_process_command_with_non_slash_command(self):
        """Test process_command ignores non-command messages."""
        # Should not crash with regular text
        telegram.process_command("12345", "hello world", 1)


class TestIntegration:
    """Integration tests for telegram module."""

    def test_telegram_enabled_depends_on_env(self):
        """Test TELEGRAM_ENABLED depends on environment variables."""
        # The value is set at module import time, so we just verify it's a boolean
        assert isinstance(telegram.TELEGRAM_ENABLED, bool)

    def test_command_handlers_dict_exists(self):
        """Test command handlers dictionary exists."""
        assert hasattr(telegram, '_command_handlers')
        assert isinstance(telegram._command_handlers, dict)

    def test_last_update_id_exists(self):
        """Test last update ID tracking variable exists."""
        assert hasattr(telegram, '_last_update_id')
        assert isinstance(telegram._last_update_id, int)

    def test_all_notification_functions_exist(self):
        """Test all notification functions are defined."""
        assert callable(telegram.notify_server_started)
        assert callable(telegram.notify_no_clients)
        assert callable(telegram.notify_client_connected)
        assert callable(telegram.notify_ip_changed)

    def test_all_core_functions_exist(self):
        """Test all core functions are defined."""
        assert callable(telegram.send_telegram_message)
        assert callable(telegram.format_datetime)
        assert callable(telegram.register_command)
        assert callable(telegram.get_updates)
        assert callable(telegram.process_command)
        assert callable(telegram.polling_loop)
        assert callable(telegram.start_polling)
