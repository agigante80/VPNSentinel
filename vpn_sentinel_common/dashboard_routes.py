"""Dashboard server routes for VPN Sentinel."""
from vpn_sentinel_common.server import dashboard_app
from vpn_sentinel_common.log_utils import log_info
from flask import render_template_string, jsonify
import os


@dashboard_app.route('/dashboard')
def dashboard():
    """Main dashboard page."""
    # Simple HTML dashboard
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>VPN Sentinel Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            h1 { color: #333; }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .ok { background-color: #d4edda; color: #155724; }
            .error { background-color: #f8d7da; color: #721c24; }
        </style>
    </head>
    <body>
        <h1>VPN Sentinel Dashboard</h1>
        <div class="status ok">
            <h2>✅ Server Status: Running</h2>
            <p>VPN Sentinel server is operational and ready to receive client keepalives.</p>
        </div>
        <div class="status ok">
            <h2>📊 Client Monitoring</h2>
            <p>Check <a href="/api/v1/status">/api/v1/status</a> for connected clients.</p>
        </div>
        <div class="status ok">
            <h2>💚 Health Checks</h2>
            <p>Health endpoints available at <a href="/health">/health</a></p>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)


@dashboard_app.route('/dashboard/')
def dashboard_slash():
    """Dashboard with trailing slash."""
    return dashboard()