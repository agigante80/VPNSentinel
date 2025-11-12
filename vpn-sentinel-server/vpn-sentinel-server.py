#!/usr/bin/env python3
"""VPN Sentinel Server entry point.

Starts the multi-app Flask server with API, health, and dashboard endpoints.
"""
import sys
import threading

# Add the app directory to Python path
sys.path.insert(0, '/app')

from vpn_sentinel_common.server import api_app, health_app, dashboard_app
from vpn_sentinel_common import api_routes, health_routes, dashboard_routes  # noqa: F401
from vpn_sentinel_common.log_utils import log_info
from vpn_sentinel_common.server_utils import run_flask_app, get_port_config
from vpn_sentinel_common.version import get_version, get_commit_hash
from vpn_sentinel_common import telegram, telegram_commands
from vpn_sentinel_common.api_routes import cleanup_stale_clients


def main():
    """Main entry point for the VPN Sentinel server."""
    import os
    
    # Log startup with version
    version = get_version()
    commit = get_commit_hash() or "unknown"
    log_info('server', f'🚀 Starting VPN Sentinel Server v{version} (commit: {commit})')

    # Initialize Telegram bot
    if telegram.TELEGRAM_ENABLED:
        log_info('telegram', '🤖 Telegram bot is enabled')
        telegram_commands.register_all_commands()
        telegram.start_polling()
        # Send startup notification
        telegram.notify_server_started(alert_threshold_min=15, check_interval_min=5)
    else:
        log_info('telegram', '⚠️ Telegram bot is disabled (no credentials configured)')

    # Get port configuration from environment
    ports = get_port_config()
    api_port = ports['api_port']
    health_port = ports['health_port']
    dashboard_port = ports['dashboard_port']
    
    # Check if web dashboard is enabled
    web_dashboard_enabled = os.getenv('VPN_SENTINEL_SERVER_WEB_DASHBOARD_ENABLED', 'true').lower() == 'true'

    # Start cleanup thread for stale clients
    cleanup_thread = threading.Thread(target=cleanup_stale_clients)
    cleanup_thread.daemon = True
    cleanup_thread.start()

    # Start servers in threads
    api_thread = threading.Thread(target=run_flask_app, args=(api_app, api_port, 'API server'))
    health_thread = threading.Thread(target=run_flask_app, args=(health_app, health_port, 'Health server'))
    
    api_thread.daemon = True
    health_thread.daemon = True

    if web_dashboard_enabled:
        dashboard_thread = threading.Thread(target=run_flask_app, args=(dashboard_app, dashboard_port, 'Dashboard server'))
        dashboard_thread.daemon = True
    else:
        log_info('server', '⚠️ Web dashboard is disabled')

    try:
        api_thread.start()
        health_thread.start()
        if web_dashboard_enabled:
            dashboard_thread.start()

        log_info('server', 'VPN Sentinel Server started successfully')

        # Keep main thread alive
        api_thread.join()

    except KeyboardInterrupt:
        log_info('server', 'Received shutdown signal')
    except Exception as e:
        log_info('server', f'Error in main server loop: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
