"""API server routes for VPN Sentinel."""
from vpn_sentinel_common.server import api_app
from vpn_sentinel_common.log_utils import log_info, log_warn
from vpn_sentinel_common import telegram
from vpn_sentinel_common.server_info import get_server_public_ip
from flask import jsonify, request
import os


# In-memory storage for client status (in production this would be a database)
client_status = {}

# Track if clients have ever connected (to avoid spam on first connect)
_client_first_seen = set()

# Cache server's public IP (fetched once at startup)
_server_public_ip = None


def get_cached_server_ip():
    """Get server's public IP (cached)."""
    global _server_public_ip
    if _server_public_ip is None:
        _server_public_ip = get_server_public_ip()
    return _server_public_ip

# Get API path from environment
API_PATH = os.getenv('VPN_SENTINEL_API_PATH', '/api/v1').strip('/')
if not API_PATH.startswith('/'):
    API_PATH = '/' + API_PATH

print(f"DEBUG: API_PATH = {API_PATH}")


@api_app.route(f'{API_PATH}/status', methods=['GET'])
def get_status():
    """Get status of all connected clients."""
    return jsonify(client_status)


@api_app.route(f'{API_PATH}/keepalive', methods=['POST'])
def keepalive():
    """Receive keepalive from a client."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        client_id = data.get('client_id')
        if not client_id:
            return jsonify({'error': 'client_id is required'}), 400

        # Extract client info (handle both flat and nested formats)
        from datetime import datetime, timezone
        vpn_ip = data.get('public_ip') or data.get('ip', 'unknown')

        # Extract location (nested or flat)
        location = data.get('location')
        if location and isinstance(location, dict) and 'country' in location:
            # Nested format
            country = location.get('country', 'unknown')
            city = location.get('city', 'unknown')
            region = location.get('region', 'unknown')
            provider = location.get('org', 'unknown')
            timezone_str = location.get('timezone', 'unknown')
        else:
            # Flat format
            country = data.get('country', 'unknown')
            city = data.get('city', 'unknown')
            region = data.get('region', 'unknown')
            provider = data.get('provider', 'unknown')
            timezone_str = data.get('timezone', 'unknown')

        # Extract DNS test (nested or flat)
        dns_test = data.get('dns_test')
        if dns_test and isinstance(dns_test, dict) and 'location' in dns_test:
            # Nested format
            dns_loc = dns_test.get('location', 'Unknown')
            dns_colo = dns_test.get('colo', 'Unknown')
        else:
            # Flat format
            dns_loc = data.get('dns_loc', 'Unknown')
            dns_colo = data.get('dns_colo', 'Unknown')

        # Check if client is new or IP changed
        is_new_client = client_id not in _client_first_seen
        old_ip = client_status.get(client_id, {}).get('ip', None) if not is_new_client else None
        ip_changed = old_ip and old_ip != vpn_ip

        # Update client status
        client_status[client_id] = {
            'last_seen': datetime.now(timezone.utc).isoformat(),
            'ip': vpn_ip,
            'location': f"{city}, {region}, {country}",
            'provider': provider,
            'country': country,
            'city': city,
            'region': region,
            'timezone': timezone_str,
            'dns_loc': dns_loc,
            'dns_colo': dns_colo
        }

        # Get server IP for comparison
        server_ip = get_cached_server_ip()
        
        # Log keepalive with VPN info
        log_info('api', f"✅ Keepalive from {client_id}")
        log_info('vpn-info', f"  📍 {city}, {country} | 🌐 {vpn_ip} | 🏢 {provider}")
        
        # Check for VPN bypass
        if vpn_ip == server_ip or vpn_ip == "unknown":
            log_warn('security', f"⚠️ VPN BYPASS WARNING: Client {client_id} has same IP as server ({vpn_ip})")

        # Send Telegram notifications
        if is_new_client:
            _client_first_seen.add(client_id)
            telegram.notify_client_connected(
                client_id, vpn_ip, f"{city}, {region}, {country}",
                city, region, country, provider, timezone_str,
                dns_loc, dns_colo, server_ip
            )
        elif ip_changed:
            telegram.notify_ip_changed(
                client_id, old_ip, vpn_ip,
                city, region, country, provider, timezone_str,
                dns_loc, dns_colo, server_ip
            )

        return jsonify({
            'status': 'ok',
            'message': 'Keepalive received',
            'server_time': datetime.now(timezone.utc).isoformat()
        })

    except Exception as e:
        log_info('api', f"Error processing keepalive: {e}")
        return jsonify({'error': 'Internal server error'}), 500
