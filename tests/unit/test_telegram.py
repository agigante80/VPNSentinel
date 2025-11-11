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


class TestProcessUpdates:
    """Tests for process_updates function."""

    def test_process_updates_empty_list(self):
        """Test processing empty update list."""
        # Should not raise exception
        telegram.process_updates([])

    def test_process_updates_with_command(self):
        """Test processing update with registered command."""
        # Register a test handler
        mock_handler = Mock()
        telegram.register_command("test", mock_handler)
        
        updates = [{
            "update_id": 1,
            "message": {
                "chat": {"id": "12345"},
                "text": "/test argument"
            }
        }]
        
        telegram.process_updates(updates)
        
        # Handler should be called
        mock_handler.assert_called_once_with("12345", "/test argument")

    def test_process_updates_unknown_command(self):
        """Test processing update with unknown command."""
        updates = [{
            "update_id": 1,
            "message": {
                "chat": {"id": "12345"},
                "text": "/unknown"
            }
        }]
        
        # Should not raise exception
        telegram.process_updates(updates)

    def test_process_updates_not_command(self):
        """Test processing update without command."""
        updates = [{
            "update_id": 1,
            "message": {
                "chat": {"id": "12345"},
                "text": "regular message"
            }
        }]
        
        # Should not raise exception
        telegram.process_updates(updates)

    def test_process_updates_updates_offset(self):
        """Test processing updates the offset."""
        updates = [{
            "update_id": 100,
            "message": {
                "chat": {"id": "12345"},
                "text": "test"
            }
        }]
        
        telegram.process_updates(updates)
        
        # Offset should be updated
        assert telegram._last_update_id >= 100


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
    def test_notify_vpn_bypass(self, mock_send):
        """Test VPN bypass notification."""
        mock_send.return_value = True
        
        result = telegram.notify_vpn_bypass("test-client", "1.2.3.4")
        
        assert result is True
        message = mock_send.call_args[0][0]
        assert "VPN BYPASS" in message
        assert "test-client" in message
        assert "1.2.3.4" in message

    @patch('vpn_sentinel_common.telegram.send_telegram_message')
    def test_notify_vpn_connected(self, mock_send):
        """Test VPN connected notification."""
        mock_send.return_value = True
        
        result = telegram.notify_vpn_connected("test-client", "1.2.3.4", "US")
        
        assert result is True
        message = mock_send.call_args[0][0]
        assert "Connected" in message
        assert "test-client" in message
        assert "1.2.3.4" in message
        assert "US" in message

    @patch('vpn_sentinel_common.telegram.send_telegram_message')
    def test_notify_client_missing(self, mock_send):
        """Test client missing notification."""
        mock_send.return_value = True
        
        result = telegram.notify_client_missing("test-client", 30)
        
        assert result is True
        message = mock_send.call_args[0][0]
        assert "Missing" in message or "No keepalive" in message
        assert "test-client" in message
        assert "30" in message


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
