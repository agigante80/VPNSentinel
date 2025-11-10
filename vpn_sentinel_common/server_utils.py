"""Server utilities for VPN Sentinel.

Provides helper functions for running Flask applications with TLS support.
"""
import os
import ssl
import sys
from werkzeug.serving import make_server
from .log_utils import log_info


def run_flask_app(app, port: int, name: str, host: str = '0.0.0.0') -> None:
    """Run a Flask app on the specified port with optional TLS.

    Args:
        app: Flask application instance
        port: Port number to bind to
        name: Human-readable name for logging
        host: Host address to bind to (default: 0.0.0.0)

    Environment Variables:
        VPN_SENTINEL_TLS_CERT_PATH: Path to TLS certificate file
        VPN_SENTINEL_TLS_KEY_PATH: Path to TLS private key file

    Raises:
        SystemExit: If server fails to start
    """
    try:
        # Check for TLS configuration
        tls_cert_path = os.getenv('VPN_SENTINEL_TLS_CERT_PATH', '')
        tls_key_path = os.getenv('VPN_SENTINEL_TLS_KEY_PATH', '')

        if tls_cert_path and tls_key_path:
            # Create SSL context for HTTPS
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(tls_cert_path, tls_key_path)
            server = make_server(host, port, app, threaded=True, ssl_context=ssl_context)
            log_info('server', f'🔒 Starting {name} on {host}:{port} with TLS')
        else:
            server = make_server(host, port, app, threaded=True)
            log_info('server', f'🌐 Starting {name} on {host}:{port}')

        server.serve_forever()

    except Exception as e:
        log_info('server', f'❌ Error starting {name}: {e}')
        sys.exit(1)


def get_port_config() -> dict:
    """Get server port configuration from environment.

    Returns:
        Dictionary with api_port, health_port, dashboard_port keys
    """
    return {
        'api_port': int(os.getenv('VPN_SENTINEL_SERVER_API_PORT', '5000')),
        'health_port': int(os.getenv('VPN_SENTINEL_SERVER_HEALTH_PORT', '8081')),
        'dashboard_port': int(os.getenv('VPN_SENTINEL_SERVER_DASHBOARD_PORT', '8080'))
    }
