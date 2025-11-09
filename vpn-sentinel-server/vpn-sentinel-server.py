#!/usr/bin/env python3
"""VPN Sentinel Server entry point.

Starts the multi-app Flask server with API, health, and dashboard endpoints.
"""
import os
import sys
import threading
import ssl
from werkzeug.serving import make_server

# Add the app directory to Python path
sys.path.insert(0, '/app')

from vpn_sentinel_common.server import api_app, health_app, dashboard_app
from vpn_sentinel_common import api_routes, health_routes, dashboard_routes
from vpn_sentinel_common.log_utils import log_info


def run_app(app, port, name):
    """Run a Flask app on the specified port."""
    try:
        # Check for TLS configuration
        tls_cert_path = os.getenv('VPN_SENTINEL_TLS_CERT_PATH', '')
        tls_key_path = os.getenv('VPN_SENTINEL_TLS_KEY_PATH', '')
        
        if tls_cert_path and tls_key_path:
            # Create SSL context for HTTPS
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(tls_cert_path, tls_key_path)
            server = make_server('0.0.0.0', port, app, threaded=True, ssl_context=ssl_context)
            log_info('server', f'Starting {name} on port {port} with TLS')
        else:
            server = make_server('0.0.0.0', port, app, threaded=True)
            log_info('server', f'Starting {name} on port {port}')
        server.serve_forever()
    except Exception as e:
        log_info('server', f'Error starting {name}: {e}')
        sys.exit(1)


def main():
    """Main entry point for the VPN Sentinel server."""
    log_info('server', 'Starting VPN Sentinel Server')
    
    # Get port configuration from environment
    api_port = int(os.getenv('VPN_SENTINEL_SERVER_API_PORT', '5000'))
    health_port = int(os.getenv('VPN_SENTINEL_SERVER_HEALTH_PORT', '8081'))
    dashboard_port = int(os.getenv('VPN_SENTINEL_SERVER_DASHBOARD_PORT', '8080'))
    
    # Start servers in threads
    api_thread = threading.Thread(target=run_app, args=(api_app, api_port, 'API server'))
    health_thread = threading.Thread(target=run_app, args=(health_app, health_port, 'Health server'))
    dashboard_thread = threading.Thread(target=run_app, args=(dashboard_app, dashboard_port, 'Dashboard server'))
    
    api_thread.daemon = True
    health_thread.daemon = True
    dashboard_thread.daemon = True
    
    try:
        api_thread.start()
        health_thread.start()
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
