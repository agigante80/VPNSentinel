"""Health server routes for VPN Sentinel."""
from vpn_sentinel_common.server import health_app
from vpn_sentinel_common.log_utils import log_info
from flask import jsonify
import os


@health_app.route('/health')
def health():
    """Basic health check endpoint."""
    return jsonify({
        'status': 'ok',
        'message': 'VPN Sentinel Health Server is running',
        'server_time': 'unknown'  # Could add timestamp if needed
    })


@health_app.route('/health/ready')
def health_ready():
    """Readiness health check."""
    return jsonify({
        'status': 'ok',
        'message': 'VPN Sentinel Health Server is ready'
    })


@health_app.route('/health/startup')
def health_startup():
    """Startup health check."""
    return jsonify({
        'status': 'ok',
        'message': 'VPN Sentinel Health Server started successfully'
    })