"""Unit tests for bot-token redaction in vpn_sentinel.common.telegram (issue #141)."""

from unittest.mock import patch, Mock

import pytest
import requests

from vpn_sentinel.common import telegram

REAL_SHAPE = "123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"
SENTINEL = "123:SENTINEL"


class StopLoop(Exception):
    """Raised from a patched time.sleep to leave polling_loop's while True."""


def _conn_error(token, method="sendMessage"):
    return requests.exceptions.ConnectionError(f"Max retries exceeded with url: /bot{token}/{method}")


class TestRedactToken:
    def test_configured_token_replaced(self):
        with patch("vpn_sentinel.common.telegram.TELEGRAM_BOT_TOKEN", "123:S"):
            assert telegram.redact_token("x /bot123:S/y") == "x /bot[REDACTED]/y"

    def test_empty_token_leaves_plain_text(self):
        with patch("vpn_sentinel.common.telegram.TELEGRAM_BOT_TOKEN", ""):
            assert telegram.redact_token("text") == "text"

    def test_token_twice(self):
        with patch("vpn_sentinel.common.telegram.TELEGRAM_BOT_TOKEN", "123:S"):
            assert telegram.redact_token("123:S and 123:S") == "[REDACTED] and [REDACTED]"

    def test_token_shape_with_empty_token(self):
        with patch("vpn_sentinel.common.telegram.TELEGRAM_BOT_TOKEN", ""):
            assert telegram.redact_token(f"url: /bot{REAL_SHAPE}/sendMessage") == "url: /bot[REDACTED]/sendMessage"

    def test_percent_encoded_trailing_newline(self):
        with patch("vpn_sentinel.common.telegram.TELEGRAM_BOT_TOKEN", REAL_SHAPE + "\n"):
            out = telegram.redact_token(f"/bot{REAL_SHAPE}%0A/sendMessage")
        assert "AAHdq" not in out
        assert "[REDACTED]" in out

    def test_non_string_is_coerced(self):
        with patch("vpn_sentinel.common.telegram.TELEGRAM_BOT_TOKEN", ""):
            assert telegram.redact_token(42) == "42"


@patch("vpn_sentinel.common.telegram.TELEGRAM_CHAT_ID", "1")
@patch("vpn_sentinel.common.telegram.TELEGRAM_BOT_TOKEN", SENTINEL)
@patch("vpn_sentinel.common.telegram.TELEGRAM_ENABLED", True)
class TestLogSitesRedact:
    @patch("vpn_sentinel.common.telegram.requests.post")
    def test_send_success_logs_no_token(self, mock_post, capsys):
        mock_post.return_value = Mock(status_code=200)
        telegram.send_telegram_message("hi")
        out = capsys.readouterr().out
        assert "Error sending message" not in out
        assert SENTINEL not in out

    @patch("vpn_sentinel.common.telegram.requests.post")
    def test_send_failure_redacted(self, mock_post, capsys):
        mock_post.side_effect = _conn_error(SENTINEL)
        telegram.send_telegram_message("hi")
        out = capsys.readouterr().out
        assert "Error sending message" in out
        assert "[REDACTED]" in out
        assert SENTINEL not in out

    @patch("vpn_sentinel.common.telegram.requests.get")
    def test_get_updates_success_no_error(self, mock_get, capsys):
        mock_get.return_value = Mock(status_code=200, json=lambda: {"ok": True, "result": []})
        assert telegram.get_updates() == []
        assert "Error getting updates" not in capsys.readouterr().out

    @patch("vpn_sentinel.common.telegram.requests.get")
    def test_get_updates_failure_redacted(self, mock_get, capsys):
        mock_get.side_effect = _conn_error(SENTINEL, "getUpdates")
        assert telegram.get_updates() == []
        out = capsys.readouterr().out
        assert "Error getting updates" in out
        assert "[REDACTED]" in out
        assert SENTINEL not in out

    def test_polling_loop_failure_redacted(self, capsys):
        with patch(
            "vpn_sentinel.common.telegram.get_updates", side_effect=Exception(f"boom /bot{SENTINEL}/getUpdates")
        ):
            with patch("vpn_sentinel.common.telegram.time.sleep", side_effect=StopLoop):
                with pytest.raises(StopLoop):
                    telegram.polling_loop()
        out = capsys.readouterr().out
        assert "Error in polling loop" in out
        assert "[REDACTED]" in out
        assert SENTINEL not in out
