"""Dashboard server routes for VPN Sentinel."""
from vpn_sentinel_common.server import dashboard_app
from vpn_sentinel_common.log_utils import log_info
from vpn_sentinel_common.server_info import get_server_info
from vpn_sentinel_common.api_routes import client_status
from flask import render_template_string
from datetime import datetime
import os


def get_client_health_status(client, server_ip):
    """Determine client health status based on IP and DNS.
    
    Returns:
        tuple: (status_class, status_icon, status_text, dns_status_icon)
        - status_class: 'status-danger', 'status-warning', or 'status-ok'
        - status_icon: emoji for overall status
        - status_text: description text
        - dns_status_icon: emoji for DNS status
    """
    client_ip = client.get('ip', 'unknown')
    dns_loc = client.get('dns_loc', 'Unknown')
    country = client.get('country', 'Unknown')
    
    # RED: Same IP as server or undetectable
    if client_ip == server_ip or client_ip == 'unknown' or client_ip == 'Unknown':
        return ('status-danger', '🔴', 'VPN Bypass Detected!', '🔴')
    
    # Check DNS leak (compare dns_loc with country)
    dns_leak = False
    if dns_loc != 'Unknown' and country != 'Unknown':
        dns_leak = (dns_loc != country)
    
    # YELLOW: Different IP but DNS leak or undetectable DNS
    if dns_leak or dns_loc == 'Unknown':
        dns_icon = '🟡' if dns_loc == 'Unknown' else '🟡'
        return ('status-warning', '🟡', 'DNS Leak Detected' if dns_leak else 'DNS Undetectable', dns_icon)
    
    # GREEN: Different IP and no DNS leak
    return ('status-ok', '🟢', 'Secure', '🟢')


@dashboard_app.route('/dashboard')
def dashboard():
    """Main dashboard page with visual client monitoring."""
    # Get server info
    server_info = get_server_info()
    server_ip = server_info.get('public_ip', 'Unknown')
    server_location = server_info.get('location', 'Unknown')
    server_provider = server_info.get('provider', 'Unknown')
    dns_status = server_info.get('dns_status', 'Unknown')
    
    # Get version
    version = os.getenv('VPN_SENTINEL_VERSION', 'dev')
    
    # Get client statistics
    total_clients = len(client_status)
    online_clients = sum(1 for c in client_status.values() if c)
    offline_clients = total_clients - online_clients
    
    # Get current time
    current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    
    # Build client rows HTML
    client_rows_html = ""
    if client_status:
        for client_id, client in client_status.items():
            health_class, health_icon, health_text, dns_icon = get_client_health_status(client, server_ip)
            
            client_ip = client.get('ip', 'unknown')
            location = client.get('location', 'Unknown')
            provider = client.get('provider', 'Unknown')
            last_seen = client.get('last_seen', 'Never')
            dns_loc = client.get('dns_loc', 'Unknown')
            dns_colo = client.get('dns_colo', 'Unknown')
            
            # Format last seen time
            try:
                last_seen_dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                time_diff = datetime.utcnow() - last_seen_dt
                if time_diff.total_seconds() < 60:
                    last_seen_str = "Just now"
                elif time_diff.total_seconds() < 3600:
                    mins = int(time_diff.total_seconds() / 60)
                    last_seen_str = f"{mins} min ago"
                else:
                    hours = int(time_diff.total_seconds() / 3600)
                    last_seen_str = f"{hours}h ago"
            except:
                last_seen_str = last_seen
            
            client_rows_html += f"""
            <tr>
                <td><strong>{client_id}</strong></td>
                <td><span class="ip-address">{client_ip}</span></td>
                <td class="location">{location}</td>
                <td class="location">{provider}</td>
                <td class="time-info">{last_seen_str}</td>
                <td>
                    <span class="status-badge {health_class}">
                        {health_icon} {health_text}
                    </span>
                </td>
                <td class="text-center">
                    <span class="dns-badge">{dns_icon}</span>
                    <div class="dns-details">{dns_loc} / {dns_colo}</div>
                </td>
            </tr>
            """
    else:
        client_rows_html = """
        <tr>
            <td colspan="7" class="no-clients">
                <div class="no-clients-icon">🔌</div>
                <h3>No VPN Clients Connected</h3>
                <p>Waiting for VPN clients to connect and report their status...</p>
            </td>
        </tr>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VPN Sentinel Dashboard</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }}
            
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
                overflow: hidden;
            }}
            
            .header {{
                background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
                color: white;
                padding: 30px;
                text-align: center;
                position: relative;
            }}
            
            .header h1 {{
                font-size: 2.5em;
                margin-bottom: 10px;
                text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
            }}
            
            .header .subtitle {{
                font-size: 1.1em;
                opacity: 0.9;
            }}
            
            .server-info {{
                position: absolute;
                top: 20px;
                right: 30px;
                background: rgba(255, 255, 255, 0.1);
                padding: 15px;
                border-radius: 10px;
                font-size: 0.9em;
                text-align: right;
                backdrop-filter: blur(10px);
            }}
            
            .server-info h4 {{
                margin: 0 0 8px 0;
                font-size: 1em;
                opacity: 0.9;
            }}
            
            .server-info .info-row {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 4px;
                min-width: 250px;
            }}
            
            .server-info .info-label {{
                opacity: 0.8;
            }}
            
            .server-info .info-value {{
                font-weight: bold;
                color: #ecf0f1;
            }}
            
            .stats {{
                display: flex;
                justify-content: center;
                gap: 30px;
                margin-top: 20px;
                flex-wrap: wrap;
            }}
            
            .stat-card {{
                background: rgba(255, 255, 255, 0.2);
                backdrop-filter: blur(10px);
                padding: 15px 25px;
                border-radius: 10px;
            }}
            
            .stat-number {{
                font-size: 2em;
                font-weight: bold;
                display: block;
            }}
            
            .stat-label {{
                font-size: 0.9em;
                opacity: 0.8;
            }}
            
            .content {{
                padding: 30px;
            }}
            
            .refresh-info {{
                text-align: center;
                margin-bottom: 25px;
                color: #666;
                font-size: 0.95em;
            }}
            
            .auto-refresh {{
                display: inline-block;
                background: #3498db;
                color: white;
                padding: 8px 15px;
                border-radius: 20px;
                font-size: 0.85em;
                animation: pulse 2s infinite;
            }}
            
            @keyframes pulse {{
                0% {{ opacity: 1; }}
                50% {{ opacity: 0.7; }}
                100% {{ opacity: 1; }}
            }}
            
            .table-container {{
                overflow-x: auto;
                border-radius: 10px;
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
            }}
            
            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                min-width: 800px;
            }}
            
            thead {{
                background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
                color: white;
            }}
            
            th, td {{
                padding: 15px 12px;
                text-align: left;
                border-bottom: 1px solid #eee;
            }}
            
            th {{
                font-weight: 600;
                text-transform: uppercase;
                font-size: 0.85em;
                letter-spacing: 0.5px;
            }}
            
            tbody tr:hover {{
                background: #f8f9fa;
                transform: translateY(-1px);
                transition: all 0.2s ease;
            }}
            
            .status-badge {{
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 0.8em;
                font-weight: bold;
                text-transform: uppercase;
                white-space: nowrap;
            }}
            
            .status-ok {{
                background: #2ecc71;
                color: white;
            }}
            
            .status-warning {{
                background: #f39c12;
                color: white;
            }}
            
            .status-danger {{
                background: #e74c3c;
                color: white;
            }}
            
            .ip-address {{
                font-family: 'Courier New', monospace;
                background: #f8f9fa;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.9em;
            }}
            
            .location {{
                font-size: 0.9em;
                color: #666;
            }}
            
            .time-info {{
                font-size: 0.85em;
                color: #888;
            }}
            
            .text-center {{
                text-align: center;
            }}
            
            .dns-badge {{
                font-size: 1.5em;
                display: block;
                margin-bottom: 4px;
            }}
            
            .dns-details {{
                font-size: 0.75em;
                color: #888;
            }}
            
            .no-clients {{
                text-align: center;
                padding: 60px 20px;
                color: #666;
            }}
            
            .no-clients-icon {{
                font-size: 4em;
                margin-bottom: 20px;
                opacity: 0.5;
            }}
            
            .footer {{
                text-align: center;
                padding: 20px;
                color: #666;
                font-size: 0.9em;
                border-top: 1px solid #eee;
            }}
            
            .footer a {{
                color: #3498db;
                text-decoration: none;
                font-weight: 600;
            }}
            
            .footer a:hover {{
                text-decoration: underline;
            }}
            
            .version-badge {{
                display: inline-block;
                background: #3498db;
                color: white;
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 0.85em;
                font-weight: bold;
                margin: 0 5px;
            }}
            
            .legend {{
                display: flex;
                justify-content: center;
                gap: 30px;
                margin: 20px 0;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 10px;
            }}
            
            .legend-item {{
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 0.9em;
            }}
            
            @media (max-width: 768px) {{
                .header {{
                    padding: 20px 15px;
                }}
                
                .header h1 {{
                    font-size: 2em;
                }}
                
                .stats {{
                    gap: 15px;
                }}
                
                .stat-card {{
                    padding: 10px 15px;
                }}
                
                .content {{
                    padding: 20px 15px;
                }}
                
                .server-info {{
                    position: static;
                    margin: 0 auto 20px auto;
                    max-width: 300px;
                    right: auto;
                    top: auto;
                }}
                
                .legend {{
                    flex-direction: column;
                    gap: 10px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="server-info">
                    <h4>🖥️ Server Details</h4>
                    <div class="info-row">
                        <span class="info-label">Public IP:</span>
                        <span class="info-value">{server_ip}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Location:</span>
                        <span class="info-value">{server_location}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Provider:</span>
                        <span class="info-value">{server_provider}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">DNS Status:</span>
                        <span class="info-value">{dns_status}</span>
                    </div>
                </div>
                
                <h1>🔒 VPN Sentinel Dashboard</h1>
                <div class="subtitle">Real-time VPN Client Monitoring</div>
                <div class="stats">
                    <div class="stat-card">
                        <span class="stat-number">{total_clients}</span>
                        <span class="stat-label">Total Clients</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-number">{online_clients}</span>
                        <span class="stat-label">Online</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-number">{offline_clients}</span>
                        <span class="stat-label">Offline</span>
                    </div>
                </div>
            </div>
            
            <div class="content">
                <div class="refresh-info">
                    <span class="auto-refresh">🔄 Auto-refresh: 30s</span> | Last updated: {current_time}
                </div>
                
                <div class="legend">
                    <div class="legend-item">
                        <span>🟢</span>
                        <span><strong>Secure:</strong> Different IP, No DNS Leak</span>
                    </div>
                    <div class="legend-item">
                        <span>🟡</span>
                        <span><strong>Warning:</strong> Different IP, DNS Leak/Undetectable</span>
                    </div>
                    <div class="legend-item">
                        <span>🔴</span>
                        <span><strong>Danger:</strong> Same IP as Server / VPN Bypass</span>
                    </div>
                </div>
                
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Client ID</th>
                                <th>VPN IP</th>
                                <th>Location</th>
                                <th>Provider</th>
                                <th>Last Seen</th>
                                <th>VPN Status</th>
                                <th>DNS Leak</th>
                            </tr>
                        </thead>
                        <tbody>
                            {client_rows_html}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div class="footer">
                <p>
                    🔒 <strong>VPN Sentinel</strong> <span class="version-badge">v{version}</span> | 
                    Server Time: {current_time} | 
                    Dashboard Port: 8080
                </p>
                <p style="margin-top: 10px;">
                    <a href="https://github.com/agigante80/VPNSentinel" target="_blank" rel="noopener noreferrer">
                        ⭐ View on GitHub
                    </a> | 
                    <a href="https://github.com/agigante80/VPNSentinel/issues" target="_blank" rel="noopener noreferrer">
                        🐛 Report Issue
                    </a> | 
                    <a href="https://github.com/agigante80/VPNSentinel/blob/main/README.md" target="_blank" rel="noopener noreferrer">
                        📖 Documentation
                    </a>
                </p>
            </div>
        </div>
        
        <script>
            // Auto-refresh the page every 30 seconds
            setTimeout(function() {{
                window.location.reload();
            }}, 30000);
        </script>
    </body>
    </html>
    """
    return render_template_string(html)


@dashboard_app.route('/dashboard/')
def dashboard_slash():
    """Dashboard with trailing slash."""
    return dashboard()