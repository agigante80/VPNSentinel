"""API server routes for VPN Sentinel."""
from vpn_sentinel_common.server import api_app
from vpn_sentinel_common.log_utils import log_info
from flask import jsonify, request
import os


# In-memory storage for client status (in production this would be a database)
client_status = {}

# Get API path from environment
API_PATH = os.getenv('VPN_SENTINEL_API_PATH', '/api/v1').strip('/')
if not API_PATH.startswith('/'):
    API_PATH = '/' + API_PATH


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

        # Update client status
        from datetime import datetime
        client_status[client_id] = {
            'last_seen': datetime.utcnow().isoformat(),
            'ip': data.get('ip', 'unknown'),
            'location': data.get('location', 'unknown'),
            'provider': data.get('provider', 'unknown')
        }

        log_info('api', f"Keepalive received from client {client_id}")
        return jsonify({
            'status': 'ok',
            'message': 'Keepalive received',
            'server_time': datetime.utcnow().isoformat()
        })

    except Exception as e:
        log_info('api', f"Error processing keepalive: {e}")
        return jsonify({'error': 'Internal server error'}), 500
