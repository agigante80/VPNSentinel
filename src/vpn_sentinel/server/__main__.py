#!/usr/bin/env python3
"""VPN Sentinel Server entry point.

Starts the multi-app Flask server with API, health, and dashboard endpoints.
"""

import sys
import threading

from vpn_sentinel.common.server import api_app, health_app, dashboard_app
from vpn_sentinel.common import api_routes, health_routes, dashboard_routes  # noqa: F401
from vpn_sentinel.common.log_utils import log_error, log_info
from vpn_sentinel.common.server_utils import run_flask_app, get_port_config, validate_tls_config
from vpn_sentinel.common.version import get_version, get_commit_hash
from vpn_sentinel.common import telegram, telegram_commands
from vpn_sentinel.common.api_routes import cleanup_stale_clients


def main():
    """Main entry point for the VPN Sentinel server."""
    import os

    # Log startup with version
    version = get_version()
    commit = get_commit_hash() or "unknown"
    log_info("server", f"🚀 Starting VPN Sentinel Server v{version} (commit: {commit})")

    # Validate TLS once, before Telegram polling or any thread starts. Fail closed, never plain HTTP.
    try:
        ssl_context = validate_tls_config(
            os.getenv("VPN_SENTINEL_TLS_CERT_PATH", ""), os.getenv("VPN_SENTINEL_TLS_KEY_PATH", "")
        )
    except ValueError as e:
        log_error("server", str(e))
        sys.exit(2)

    # Initialize Telegram bot
    if telegram.TELEGRAM_ENABLED:
        log_info("telegram", "🤖 Telegram bot is enabled")
        telegram_commands.register_all_commands()
        telegram.start_polling()
        # Send startup notification
        telegram.notify_server_started(alert_threshold_min=15, check_interval_min=5)
    else:
        log_info("telegram", "⚠️ Telegram bot is disabled (no credentials configured)")

    # Get port configuration from environment
    ports = get_port_config()
    api_port = ports["api_port"]
    health_port = ports["health_port"]
    dashboard_port = ports["dashboard_port"]

    # Check if web dashboard is enabled
    web_dashboard_enabled = os.getenv("VPN_SENTINEL_SERVER_WEB_DASHBOARD_ENABLED", "true").lower() == "true"

    # Start cleanup thread for stale clients
    cleanup_thread = threading.Thread(target=cleanup_stale_clients)
    cleanup_thread.daemon = True
    cleanup_thread.start()

    # Shared failure signal: a listener that dies must take the whole process down (exit 1)
    failure_event = threading.Event()
    failed_names = []

    def listener(app, port, name):
        try:
            run_flask_app(app, port, name, ssl_context=ssl_context, failure_event=failure_event)
        except SystemExit:
            failed_names.append(name)
            failure_event.set()

    listeners = [
        threading.Thread(target=listener, args=(api_app, api_port, "API server"), daemon=True),
        threading.Thread(target=listener, args=(health_app, health_port, "Health server"), daemon=True),
    ]
    if web_dashboard_enabled:
        listeners.append(
            threading.Thread(target=listener, args=(dashboard_app, dashboard_port, "Dashboard server"), daemon=True)
        )
    else:
        log_info("server", "⚠️ Web dashboard is disabled")

    try:
        for thread in listeners:
            thread.start()

        log_info("server", "VPN Sentinel Server started successfully")

        # Keep main thread alive until a listener dies
        while not failure_event.wait(timeout=1):
            pass

        names = ", ".join(failed_names) or "a listener"
        log_error("server", f"{names} failed, shutting down")
        sys.exit(1)

    except KeyboardInterrupt:
        log_info("server", "Received shutdown signal")
    except Exception as e:
        log_error("server", f"Error in main server loop: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
