"""Tests for vpn_sentinel.common.notifications: Telegram plus optional Apprise fan-out (issue #142).

The Apprise send runs on one daemon worker thread. Every assertion about a delivery or a `notify`
warning therefore calls `notifications.flush()` first and asserts it returned True. The autouse
fixture in tests/unit/conftest.py resets the worker and the `apprise` logger level around each test.
"""

import logging
import os
import subprocess
import sys
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from vpn_sentinel.common import notifications, telegram

PYTHON = sys.executable or "python3"
TOKEN = "s3cr3t-tok3n"


def _result(name):
    from apprise import AppriseResultStatus

    return SimpleNamespace(status=getattr(AppriseResultStatus, name))


@pytest.fixture
def tg_on():
    with (
        patch.object(telegram, "TELEGRAM_ENABLED", True),
        patch.object(telegram, "send_telegram_message", return_value=True) as send,
    ):
        yield send


@pytest.fixture
def tg_off():
    with (
        patch.object(telegram, "TELEGRAM_ENABLED", False),
        patch.object(telegram, "send_telegram_message", return_value=False) as send,
    ):
        yield send


@pytest.fixture
def blocking_sender():
    """A sender that blocks until the test releases it; released in teardown so no thread outlives the test."""
    started = threading.Event()
    release = threading.Event()
    calls = []

    def sender(targets, title, body):
        calls.append((list(targets), title, body))
        started.set()
        release.wait(30)
        return _result("SUCCESS")

    with patch.object(notifications, "_apprise_send", side_effect=sender):
        yield SimpleNamespace(started=started, release=release, calls=calls)
        release.set()


class TestTargets:
    def test_unset_is_empty(self):
        assert notifications._apprise_targets() == []

    def test_whitespace_only_is_empty_and_silent(self, monkeypatch):
        monkeypatch.setenv("VPN_SENTINEL_APPRISE_URLS", "   ")
        with patch.object(notifications, "log_warn") as warn:
            assert notifications._apprise_targets() == []
        warn.assert_not_called()

    def test_comma_and_whitespace_separated_blanks_dropped(self, monkeypatch):
        monkeypatch.setenv("VPN_SENTINEL_APPRISE_URLS", " json://a/x ,, ntfys://t\n\tgotify://h/k , ")
        assert notifications._apprise_targets() == ["json://a/x", "ntfys://t", "gotify://h/k"]

    def test_read_through_file_form(self, monkeypatch, tmp_path):
        f = tmp_path / "urls"
        f.write_text("json://a/x ntfys://t\n")
        monkeypatch.setenv("VPN_SENTINEL_APPRISE_URLS_FILE", str(f))
        assert notifications._apprise_targets() == ["json://a/x", "ntfys://t"]

    def test_both_env_and_file_is_an_error_naming_no_content(self, monkeypatch, tmp_path):
        f = tmp_path / "urls"
        f.write_text(f"json://a/{TOKEN}")
        monkeypatch.setenv("VPN_SENTINEL_APPRISE_URLS_FILE", str(f))
        monkeypatch.setenv("VPN_SENTINEL_APPRISE_URLS", f"json://b/{TOKEN}")
        with pytest.raises(ValueError) as exc:
            notifications._apprise_targets()
        assert TOKEN not in str(exc.value)


class TestPrepareUrl:
    def test_text_format_and_timeouts_appended(self):
        assert notifications._prepare_url("json://h/p") == "json://h/p?format=text&cto=3&rto=3"

    def test_appends_with_ampersand_when_query_exists(self):
        assert notifications._prepare_url("json://h/p?x=1") == "json://h/p?x=1&format=text&cto=3&rto=3"

    def test_own_format_is_kept(self):
        out = notifications._prepare_url("json://h/p?format=html")
        assert "format=html" in out and "format=text" not in out
        assert "cto=3" in out and "rto=3" in out

    def test_own_timeout_is_kept(self):
        out = notifications._prepare_url("json://h/p?cto=10")
        assert "cto=10" in out and "cto=3" not in out
        assert "rto=3" in out and "format=text" in out

    def test_param_names_match_whole_keys_only(self):
        out = notifications._prepare_url("json://h/p?myformat=html&xcto=1")
        assert "format=text" in out and "cto=3" in out


class TestRedact:
    @pytest.mark.parametrize(
        "url,expected",
        [
            (f"ntfys://{TOKEN}", "ntfys://***"),
            (f"notaservice://{TOKEN}", "notaservice://***"),
            (f"json://host/{TOKEN}?x=1", "json://***"),
            (TOKEN, "invalid://***"),
            (f"we ird://{TOKEN}", "invalid://***"),
        ],
    )
    def test_only_the_scheme_survives(self, url, expected):
        assert notifications._redact(url) == expected


class TestNotifyRouting:
    def test_unset_calls_telegram_once_and_not_apprise(self, tg_on):
        with patch.object(notifications, "_apprise_send") as send:
            assert notifications.notify("t", "<b>x</b>") is True
            assert notifications.flush() is True
        tg_on.assert_called_once_with("<b>x</b>")
        send.assert_not_called()

    def test_unset_does_not_import_apprise(self):
        code = (
            "import sys\n"
            "from unittest.mock import patch\n"
            "from vpn_sentinel.common import notifications, telegram\n"
            "with patch.object(telegram, 'TELEGRAM_ENABLED', True), patch.object(telegram, 'send_telegram_message', return_value=True) as s:\n"
            "    assert notifications.notify('t', '<b>x</b>') is True\n"
            "    assert notifications.flush() is True\n"
            "    s.assert_called_once()\n"
            "assert 'apprise' not in sys.modules, 'apprise was imported'\n"
        )
        r = _run_py(code)
        assert r.returncode == 0, r.stdout + r.stderr

    def test_telegram_disabled_apprise_set_skips_telegram_and_its_warning(self, tg_off, monkeypatch, capsys):
        monkeypatch.setenv("VPN_SENTINEL_APPRISE_URLS", "json://h/x")
        with patch.object(notifications, "_apprise_send", return_value=_result("SUCCESS")) as send:
            assert notifications.notify("Title", "<b>x</b>") is False
            assert notifications.flush() is True
        tg_off.assert_not_called()
        send.assert_called_once()
        targets, title, body = send.call_args[0]
        assert targets == ["json://h/x"] and title == "Title" and body == "<b>x</b>"
        assert "not configured" not in capsys.readouterr().out

    def test_both_enabled_delivers_to_both(self, tg_on, monkeypatch):
        monkeypatch.setenv("VPN_SENTINEL_APPRISE_URLS", "json://h/x")
        with patch.object(notifications, "_apprise_send", return_value=_result("SUCCESS")) as send:
            assert notifications.notify("t", "b") is True
            assert notifications.flush() is True
        tg_on.assert_called_once_with("b")
        send.assert_called_once()

    def test_bad_file_secret_never_raises_and_telegram_still_sent(self, tg_on, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("VPN_SENTINEL_APPRISE_URLS_FILE", str(tmp_path / "missing"))
        assert notifications.notify("t", "b") is True
        tg_on.assert_called_once()
        assert "[notify]" in capsys.readouterr().out


class TestDelivery:
    def test_json_target_gets_plain_text_once(self, tg_off, monkeypatch, httpserver):
        httpserver.expect_request("/hook", method="POST").respond_with_data("ok")
        monkeypatch.setenv("VPN_SENTINEL_APPRISE_URLS", f"json://127.0.0.1:{httpserver.port}/hook")
        notifications.notify("T", "<b>x</b>")
        assert notifications.flush() is True
        assert len(httpserver.log) == 1
        body = httpserver.log[0][0].get_json()
        assert body["message"] == "x"
        assert "<b>" not in body["message"]

    def test_clients_silent_one_post_with_both_ids(self, tg_off, monkeypatch, httpserver):
        httpserver.expect_request("/hook", method="POST").respond_with_data("ok")
        monkeypatch.setenv("VPN_SENTINEL_APPRISE_URLS", f"json://127.0.0.1:{httpserver.port}/hook")
        telegram.notify_clients_silent([("alpha-vpn", 20), ("beta-vpn", 31)])
        assert notifications.flush() is True
        assert len(httpserver.log) == 1
        message = httpserver.log[0][0].get_json()["message"]
        assert "alpha-vpn" in message and "beta-vpn" in message
        assert "<b>" not in message and "<code>" not in message

    def test_target_500_warns_with_scheme_only_and_telegram_still_sent(
        self, tg_on, monkeypatch, httpserver, capsys, caplog
    ):
        httpserver.expect_request(f"/{TOKEN}", method="POST").respond_with_data("boom", status=500)
        monkeypatch.setenv("VPN_SENTINEL_APPRISE_URLS", f"json://127.0.0.1:{httpserver.port}/{TOKEN}")
        with caplog.at_level(logging.DEBUG, logger="apprise"):
            assert notifications.notify("t", "b") is True
            assert notifications.flush() is True
        out = capsys.readouterr().out
        assert "[notify]" in out and "json://***" in out
        assert TOKEN not in out
        assert TOKEN not in _apprise_log_text(caplog)
        tg_on.assert_called_once()

    def test_unknown_scheme_does_not_leak_token(self, tg_on, monkeypatch, capsys, caplog):
        monkeypatch.setenv("VPN_SENTINEL_APPRISE_URLS", f"notaservice://{TOKEN}")
        with caplog.at_level(logging.DEBUG, logger="apprise"):
            assert notifications.notify("t", "b") is True
            assert notifications.flush() is True
        out = capsys.readouterr().out
        assert "notaservice://***" in out
        assert TOKEN not in out and TOKEN not in _apprise_log_text(caplog)
        tg_on.assert_called_once()

    def test_one_failing_target_does_not_block_the_other(self, tg_off, monkeypatch, httpserver):
        httpserver.expect_request("/ok", method="POST").respond_with_data("ok")
        monkeypatch.setenv("VPN_SENTINEL_APPRISE_URLS", f"notaservice://x json://127.0.0.1:{httpserver.port}/ok")
        notifications.notify("t", "<b>x</b>")
        assert notifications.flush() is True
        assert len(httpserver.log) == 1

    @pytest.mark.parametrize("status", ["FAILURE", "TIMEOUT", "PARTIAL", "NOMATCH"])
    def test_every_non_success_status_warns_once(self, tg_off, monkeypatch, capsys, status):
        monkeypatch.setenv("VPN_SENTINEL_APPRISE_URLS", f"json://h/{TOKEN}")
        with patch.object(notifications, "_apprise_send", return_value=_result(status)):
            notifications.notify("t", "b")
            assert notifications.flush() is True
        out = capsys.readouterr().out
        assert out.count("[notify]") == 1
        assert status in out and TOKEN not in out

    def test_success_does_not_warn(self, tg_off, monkeypatch, capsys):
        monkeypatch.setenv("VPN_SENTINEL_APPRISE_URLS", "json://h/x")
        with patch.object(notifications, "_apprise_send", return_value=_result("SUCCESS")):
            notifications.notify("t", "b")
            assert notifications.flush() is True
        assert "[notify]" not in capsys.readouterr().out

    def test_sender_raising_does_not_time_out_flush(self, tg_off, monkeypatch, capsys):
        monkeypatch.setenv("VPN_SENTINEL_APPRISE_URLS", f"json://h/{TOKEN}")
        with patch.object(notifications, "_apprise_send", side_effect=RuntimeError(f"boom {TOKEN}")):
            notifications.notify("t", "b")
            assert notifications.flush(timeout=2.0) is True
            # The worker survived: a second item is still processed.
            notifications.notify("t", "b")
            assert notifications.flush(timeout=2.0) is True
        out = capsys.readouterr().out
        assert out.count("[notify]") == 2
        assert "RuntimeError" in out and TOKEN not in out

    def test_worker_sets_apprise_logger_critical(self, tg_off, monkeypatch):
        logging.getLogger("apprise").setLevel(logging.DEBUG)
        monkeypatch.setenv("VPN_SENTINEL_APPRISE_URLS", "json://h/x")
        with patch.object(notifications, "_apprise_send", return_value=_result("SUCCESS")):
            notifications.notify("t", "b")
            assert notifications.flush() is True
        assert logging.getLogger("apprise").level == logging.CRITICAL


class TestMissingApprise:
    def test_not_installed_warns_once_and_telegram_still_sent(self):
        code = (
            "import sys\n"
            "sys.modules['apprise'] = None  # makes `import apprise` raise ImportError\n"
            "from unittest.mock import patch\n"
            "from vpn_sentinel.common import notifications, telegram\n"
            "with patch.object(telegram, 'TELEGRAM_ENABLED', True), patch.object(telegram, 'send_telegram_message', return_value=True) as s:\n"
            "    assert notifications.notify('t', 'b') is True\n"
            "    assert notifications.notify('t', 'b') is True\n"
            "    assert notifications.flush() is True\n"
            "    assert s.call_count == 2\n"
        )
        r = _run_py(code, {"VPN_SENTINEL_APPRISE_URLS": f"json://h/{TOKEN}"})
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        assert out.count("apprise not installed") == 1
        assert TOKEN not in out and "Traceback" not in out


class TestBoundedQueue:
    def test_full_queue_drops_with_warning_and_returns_immediately(self, tg_off, monkeypatch, blocking_sender, capsys):
        monkeypatch.setenv("VPN_SENTINEL_APPRISE_URLS", "json://h/x")
        notifications.notify("t", "first")
        assert blocking_sender.started.wait(5)
        for i in range(notifications.APPRISE_QUEUE_MAX):
            notifications.notify("t", f"queued {i}")
        capsys.readouterr()
        started = time.monotonic()
        notifications.notify("t", "overflow")
        assert time.monotonic() - started < 1.0
        assert "apprise queue full" in capsys.readouterr().out

    def test_reset_does_not_block_on_a_full_queue(self, tg_off, monkeypatch, blocking_sender):
        monkeypatch.setenv("VPN_SENTINEL_APPRISE_URLS", "json://h/x")
        notifications.notify("t", "first")
        assert blocking_sender.started.wait(5)
        for i in range(notifications.APPRISE_QUEUE_MAX):
            notifications.notify("t", f"queued {i}")
        started = time.monotonic()
        notifications._reset_for_tests()
        assert time.monotonic() - started < 5.0

    def test_flush_returns_false_on_timeout_and_its_helper_is_a_daemon(self, tg_off, monkeypatch, blocking_sender):
        monkeypatch.setenv("VPN_SENTINEL_APPRISE_URLS", "json://h/x")
        notifications.notify("t", "first")
        assert blocking_sender.started.wait(5)
        assert notifications.flush(timeout=0.2) is False
        helpers = [t for t in threading.enumerate() if t.name == "notifications-flush"]
        assert helpers and all(t.daemon for t in helpers)

    def test_flush_with_nothing_queued_is_true(self):
        assert notifications.flush(timeout=1.0) is True


def _apprise_log_text(caplog):
    """Only what the `apprise` logger emitted (the test receiver's own werkzeug log shows request paths)."""
    return "\n".join(r.getMessage() for r in caplog.records if r.name.split(".")[0] == "apprise")


def _run_py(code, env_extra=None):
    env = os.environ.copy()
    env.pop("VPN_SENTINEL_APPRISE_URLS", None)
    env.pop("VPN_SENTINEL_APPRISE_URLS_FILE", None)
    env.update(env_extra or {})
    env["PYTHONPATH"] = os.getcwd() + os.pathsep + os.path.join(os.getcwd(), "src")
    return subprocess.run([PYTHON, "-c", code], env=env, capture_output=True, text=True, cwd=os.getcwd(), timeout=60)
