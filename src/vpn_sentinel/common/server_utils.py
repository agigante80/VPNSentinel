"""Server utilities for VPN Sentinel.

Provides helper functions for running Flask applications with TLS support.
"""

import os
import ssl
import sys
from werkzeug.serving import make_server
from .log_utils import log_info


def validate_tls_config(cert_path, key_path):
    """Validate the server TLS configuration and build an SSL context.

    Fails closed: when either path is set, both must be set, exist, be readable
    and load as a matching pair. There is no fallback to plain HTTP.

    Args:
        cert_path: Value of VPN_SENTINEL_TLS_CERT_PATH (empty or None when unset)
        key_path: Value of VPN_SENTINEL_TLS_KEY_PATH (empty or None when unset)

    Returns:
        A ready ssl.SSLContext, or None when neither path is set (plain HTTP).

    Raises:
        ValueError: With a specific message naming the env var at fault.
    """
    cert_path = cert_path or ""
    key_path = key_path or ""
    if not cert_path and not key_path:
        return None

    if cert_path and not key_path:
        raise ValueError(
            "VPN_SENTINEL_TLS_CERT_PATH is set but VPN_SENTINEL_TLS_KEY_PATH is not: the server needs both. "
            "If this is a shared .env where the cert is only a client CA bundle, move it to the client's environment"
        )
    if key_path and not cert_path:
        raise ValueError(
            "VPN_SENTINEL_TLS_KEY_PATH is set but VPN_SENTINEL_TLS_CERT_PATH is not: the server needs both"
        )

    checks = (
        ("certificate", cert_path, "VPN_SENTINEL_TLS_CERT_PATH"),
        ("key", key_path, "VPN_SENTINEL_TLS_KEY_PATH"),
    )
    for label, path, var in checks:
        if not os.path.isfile(path):
            raise ValueError(f"TLS {label} not found: {path} ({var})")
        if not os.access(path, os.R_OK):
            raise ValueError(f"TLS {label} not readable: {path} ({var})")

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    try:
        context.load_cert_chain(cert_path, key_path)
    except (ssl.SSLError, OSError) as e:
        raise ValueError(
            f"TLS could not load certificate/key pair ({cert_path}, {key_path}): {e}. "
            "Check VPN_SENTINEL_TLS_CERT_PATH and VPN_SENTINEL_TLS_KEY_PATH match"
        ) from e
    return context


def run_flask_app(app, port: int, name: str, host: str = "0.0.0.0", ssl_context=None, failure_event=None) -> None:
    """Run a Flask app on the specified port with optional TLS.

    Args:
        app: Flask application instance
        port: Port number to bind to
        name: Human-readable name for logging
        host: Host address to bind to (default: 0.0.0.0)
        ssl_context: Pre-validated SSL context from validate_tls_config (None = plain HTTP)
        failure_event: Optional threading.Event set when this listener dies

    Raises:
        SystemExit: If server fails to start
    """
    try:
        import logging

        # Get the component name for logging (e.g., "API server" -> "api")
        component = name.replace(" server", "").lower()

        # Create custom logging handler that uses our log_info format
        class VPNSentinelLogHandler(logging.Handler):
            def __init__(self, component_name):
                super().__init__()
                self.component_name = component_name

            def emit(self, record):
                try:
                    msg = record.getMessage()
                    # Skip Flask startup messages
                    if msg.startswith(" * "):
                        return

                    # Parse Werkzeug format: IP - - [timestamp] "METHOD PATH HTTP/version" STATUS -
                    if '"' in msg:
                        parts = msg.split('"')
                        if len(parts) >= 2:
                            ip_part = parts[0].strip()
                            request_part = parts[1].strip()
                            status_part = parts[2].strip() if len(parts) > 2 else ""

                            # Extract components
                            ip = ip_part.split()[0] if ip_part else "unknown"
                            method = request_part.split()[0] if request_part else ""
                            path_parts = request_part.split()
                            path = (
                                " ".join(path_parts[1:-1])
                                if len(path_parts) > 2
                                else (path_parts[1] if len(path_parts) > 1 else "")
                            )
                            status = status_part.split()[0] if status_part else ""

                            # Use our standardized log format
                            log_info(self.component_name, f'🌐 {ip} "{method} {path}" {status}')
                        else:
                            log_info(self.component_name, msg)
                    else:
                        log_info(self.component_name, msg)
                except Exception:
                    pass

        # Create custom request handler that uses our log format
        from werkzeug.serving import WSGIRequestHandler

        class CustomRequestHandler(WSGIRequestHandler):
            def log_request(self, code="-", size="-"):
                """Log HTTP request using VPN Sentinel format"""
                try:
                    # Build request string like "GET /path HTTP/1.1"
                    request_line = f"{self.command} {self.path}"
                    if hasattr(self, "request_version"):
                        request_line += f" {self.request_version}"

                    # Get client IP
                    client_ip = self.address_string()

                    # Use our log_info format
                    log_info(component, f'🌐 {client_ip} "{request_line}" {code}')
                except Exception:
                    pass

        # Disable the default Werkzeug logger to prevent duplicate logs
        logging.getLogger("werkzeug").setLevel(logging.ERROR)

        if ssl_context is not None:
            server = make_server(
                host, port, app, threaded=True, ssl_context=ssl_context, request_handler=CustomRequestHandler
            )
            log_info("server", f"🔒 Starting {name} on {host}:{port} with TLS")
        else:
            server = make_server(host, port, app, threaded=True, request_handler=CustomRequestHandler)
            log_info("server", f"🌐 Starting {name} on {host}:{port}")

        server.serve_forever()

    except Exception as e:
        log_info("server", f"❌ Error starting {name}: {e}")
        if failure_event is not None:
            failure_event.set()
        sys.exit(1)


def get_port_config() -> dict:
    """Get server port configuration from environment.

    Returns:
        Dictionary with api_port, health_port, dashboard_port keys
    """
    return {
        "api_port": int(os.getenv("VPN_SENTINEL_SERVER_API_PORT", "5000")),
        "health_port": int(os.getenv("VPN_SENTINEL_SERVER_HEALTH_PORT", "8081")),
        "dashboard_port": int(os.getenv("VPN_SENTINEL_SERVER_DASHBOARD_PORT", "8080")),
    }
