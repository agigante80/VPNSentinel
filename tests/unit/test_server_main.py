"""Tests for vpn_sentinel.server.__main__.main(): TLS fail-fast and listener death."""

import threading
from unittest.mock import MagicMock, patch

import pytest

from vpn_sentinel.server import __main__ as server_main

TLS_ENV = ("VPN_SENTINEL_TLS_CERT_PATH", "VPN_SENTINEL_TLS_KEY_PATH")


@pytest.fixture
def clean_env(monkeypatch):
    for name in TLS_ENV:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def _run_main_expect_exit(env, **patches):
    with (
        patch.object(server_main.telegram, "TELEGRAM_ENABLED", True),
        patch.object(server_main.telegram, "start_polling") as polling,
        patch.object(server_main.telegram_commands, "register_all_commands"),
        patch.object(server_main.telegram, "notify_server_started"),
        patch.object(server_main.threading.Thread, "start") as thread_start,
        patch.object(server_main, "log_error") as log_error,
    ):
        with pytest.raises(SystemExit) as exc:
            server_main.main()
    return exc.value.code, log_error, polling, thread_start


class TestTlsFailFast:
    def test_cert_set_key_missing_exits_2(self, clean_env):
        clean_env.setenv("VPN_SENTINEL_TLS_CERT_PATH", "/certs/x.pem")
        code, log_error, polling, thread_start = _run_main_expect_exit(None)
        assert code == 2
        log_error.assert_called_once()
        assert log_error.call_args[0][0] == "server"
        assert "VPN_SENTINEL_TLS_KEY_PATH" in log_error.call_args[0][1]
        thread_start.assert_not_called()
        polling.assert_not_called()

    def test_cert_not_found_exits_2_exact_message(self, clean_env, tmp_path):
        key = tmp_path / "k.pem"
        key.write_text("x")
        missing = str(tmp_path / "missing.pem")
        clean_env.setenv("VPN_SENTINEL_TLS_CERT_PATH", missing)
        clean_env.setenv("VPN_SENTINEL_TLS_KEY_PATH", str(key))
        code, log_error, polling, thread_start = _run_main_expect_exit(None)
        assert code == 2
        log_error.assert_called_once_with(
            "server", f"TLS certificate not found: {missing} (VPN_SENTINEL_TLS_CERT_PATH)"
        )
        thread_start.assert_not_called()
        polling.assert_not_called()


class TestListenerDeath:
    def test_health_listener_death_exits_1(self, clean_env):
        def fake_run(app, port, name, host="0.0.0.0", ssl_context=None):
            if name == "Health server":
                raise SystemExit(1)
            threading.Event().wait(5)

        with (
            patch.object(server_main.telegram, "TELEGRAM_ENABLED", False),
            patch.object(server_main, "run_flask_app", side_effect=fake_run),
            patch.object(server_main, "cleanup_stale_clients", lambda: None),
            patch.object(server_main, "log_error") as log_error,
        ):
            with pytest.raises(SystemExit) as exc:
                server_main.main()
        assert exc.value.code == 1
        log_error.assert_called_once_with("server", "Health server failed, shutting down")

    def test_context_passed_to_every_listener(self, clean_env):
        seen = {}
        ctx = MagicMock()

        def fake_run(app, port, name, host="0.0.0.0", ssl_context=None):
            seen[name] = ssl_context
            if len(seen) == 3:
                raise SystemExit(1)
            threading.Event().wait(5)

        with (
            patch.object(server_main.telegram, "TELEGRAM_ENABLED", False),
            patch.object(server_main, "validate_tls_config", return_value=ctx),
            patch.object(server_main, "run_flask_app", side_effect=fake_run),
            patch.object(server_main, "cleanup_stale_clients", lambda: None),
            patch.object(server_main, "log_error"),
        ):
            with pytest.raises(SystemExit):
                server_main.main()
        assert seen == {"API server": ctx, "Health server": ctx, "Dashboard server": ctx}


class TestDashboardToggle:
    """VPN_SENTINEL_SERVER_WEB_DASHBOARD_ENABLED decides whether a dashboard listener exists."""

    def _listener_names(self, clean_env, value):
        clean_env.setenv("VPN_SENTINEL_SERVER_WEB_DASHBOARD_ENABLED", value)
        names = []

        def fake_run(app, port, name, host="0.0.0.0", ssl_context=None):
            names.append(name)
            if name == "Health server":
                raise SystemExit(1)
            threading.Event().wait(5)

        with (
            patch.object(server_main.telegram, "TELEGRAM_ENABLED", False),
            patch.object(server_main, "run_flask_app", side_effect=fake_run),
            patch.object(server_main, "cleanup_stale_clients", lambda: None),
            patch.object(server_main, "log_error"),
            patch.object(server_main, "log_info") as log_info,
        ):
            with pytest.raises(SystemExit):
                server_main.main()
        return names, log_info

    def test_disabled_starts_no_dashboard_listener(self, clean_env):
        names, log_info = self._listener_names(clean_env, "false")
        assert names, "the other listeners must still start, or this test proves nothing"
        assert "Dashboard server" not in names
        assert any("Web dashboard is disabled" in str(c.args[1]) for c in log_info.call_args_list)

    def test_enabled_starts_dashboard_listener(self, clean_env):
        names, log_info = self._listener_names(clean_env, "true")
        assert "Dashboard server" in names
        assert not any("Web dashboard is disabled" in str(c.args[1]) for c in log_info.call_args_list)
