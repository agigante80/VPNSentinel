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
        import logging
        
        # Get the component name for logging (e.g., "API server" -> "api")
        component = name.replace(' server', '').lower()
        
        # Create custom logging handler that uses our log_info format
        class VPNSentinelLogHandler(logging.Handler):
            def __init__(self, component_name):
                super().__init__()
                self.component_name = component_name
            
            def emit(self, record):
                try:
                    msg = record.getMessage()
                    # Skip Flask startup messages
                    if msg.startswith(' * '):
                        return
                    
                    # Parse Werkzeug format: IP - - [timestamp] "METHOD PATH HTTP/version" STATUS -
                    if '"' in msg:
                        parts = msg.split('"')
                        if len(parts) >= 2:
                            ip_part = parts[0].strip()
                            request_part = parts[1].strip()
                            status_part = parts[2].strip() if len(parts) > 2 else ''
                            
                            # Extract components
                            ip = ip_part.split()[0] if ip_part else 'unknown'
                            method = request_part.split()[0] if request_part else ''
                            path_parts = request_part.split()
                            path = ' '.join(path_parts[1:-1]) if len(path_parts) > 2 else (path_parts[1] if len(path_parts) > 1 else '')
                            status = status_part.split()[0] if status_part else ''
                            
                            # Use our standardized log format
                            log_info(self.component_name, f"🌐 {ip} \"{method} {path}\" {status}")
                        else:
                            log_info(self.component_name, msg)
                    else:
                        log_info(self.component_name, msg)
                except:
                    pass
        
        # Create custom request handler that uses our log format
        from werkzeug.serving import WSGIRequestHandler
        
        class CustomRequestHandler(WSGIRequestHandler):
            def log_request(self, code='-', size='-'):
                """Log HTTP request using VPN Sentinel format"""
                try:
                    # Build request string like "GET /path HTTP/1.1"
                    request_line = f"{self.command} {self.path}"
                    if hasattr(self, 'request_version'):
                        request_line += f" {self.request_version}"
                    
                    # Get client IP
                    client_ip = self.address_string()
                    
                    # Use our log_info format
                    log_info(component, f"🌐 {client_ip} \"{request_line}\" {code}")
                except:
                    pass
        
        # Disable the default Werkzeug logger to prevent duplicate logs
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        
        # Check for TLS configuration
        tls_cert_path = os.getenv('VPN_SENTINEL_TLS_CERT_PATH', '')
        tls_key_path = os.getenv('VPN_SENTINEL_TLS_KEY_PATH', '')

        if tls_cert_path and tls_key_path:
            # Create SSL context for HTTPS
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(tls_cert_path, tls_key_path)
            server = make_server(host, port, app, threaded=True, ssl_context=ssl_context, 
                               request_handler=CustomRequestHandler)
            log_info('server', f'🔒 Starting {name} on {host}:{port} with TLS')
        else:
            server = make_server(host, port, app, threaded=True, 
                               request_handler=CustomRequestHandler)
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
