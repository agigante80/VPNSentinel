"""
Test fixtures and sample data for VPN Sentinel tests
"""

# Sample keepalive request payload
SAMPLE_KEEPALIVE_REQUEST = {
    "client_id": "test-client-001",
    "timestamp": "2025-10-13T20:45:59+00:00", 
    "public_ip": "172.67.163.127",
    "status": "alive",
    "location": {
        "country": "ES",
        "city": "Madrid", 
        "region": "Madrid",
        "org": "AS57269 DIGI SPAIN TELECOM S.L.",
        "timezone": "Europe/Madrid"
    },
    "dns_test": {
        "location": "ES",
        "colo": "MAD"
    }
}

# Sample client with different IP (VPN working)
SAMPLE_VPN_CLIENT = {
    "client_id": "vpn-client-001",
    "timestamp": "2025-10-13T20:45:59+00:00", 
    "public_ip": "140.82.121.4",
    "status": "alive",
    "location": {
        "country": "PL",
        "city": "Toruń", 
        "region": "Kujawsko-Pomorskie",
        "org": "AS50599 DATASPACE P.S.A.",
        "timezone": "Europe/Warsaw"
    },
    "dns_test": {
        "location": "PL",
        "colo": "WAW"
    }
}

# Sample client with same IP as server (VPN bypass)
SAMPLE_SAME_IP_CLIENT = {
    "client_id": "same-ip-client",
    "timestamp": "2025-10-13T20:45:59+00:00", 
    "public_ip": "172.67.163.127",  # Same as server
    "status": "alive",
    "location": {
        "country": "ES",
        "city": "Madrid", 
        "region": "Madrid",
        "org": "AS57269 DIGI SPAIN TELECOM S.L.",
        "timezone": "Europe/Madrid"
    },
    "dns_test": {
        "location": "ES",
        "colo": "MAD"
    }
}

# Sample server info response
SAMPLE_SERVER_INFO = {
    "ip": "172.67.163.127",
    "city": "Madrid",
    "region": "Madrid", 
    "country": "ES",
    "org": "AS57269 DIGI SPAIN TELECOM S.L.",
    "timezone": "Europe/Madrid"
}

# Sample environment variables for testing
TEST_ENV_VARS = {
    'VPN_SENTINEL_API_KEY': 'test-api-key-abcdef123456',
    'VPN_SENTINEL_SERVER_API_PORT': '5000',
    'VPN_SENTINEL_SERVER_DASHBOARD_PORT': '5553',
    'VPN_SENTINEL_SERVER_DASHBOARD_ENABLED': 'true',
    'VPN_SENTINEL_ALERT_THRESHOLD_MINUTES': '15',
    'VPN_SENTINEL_CHECK_INTERVAL_MINUTES': '5',
    'TELEGRAM_BOT_TOKEN': 'test:bot_token_here',
    'TELEGRAM_CHAT_ID': '123456789',
    'TZ': 'UTC'
}

# Expected Telegram status messages
EXPECTED_STATUS_ONLINE = "🟢 test-client - Online"
EXPECTED_STATUS_WARNING = "⚠️ same-ip-client - Online (Same IP as server)" 
EXPECTED_STATUS_OFFLINE = "🔴 offline-client - Offline"

# Sample dashboard template data
SAMPLE_DASHBOARD_DATA = {
    'clients': [
        {
            'id': 'test-client-001',
            'status_text': 'Online',
            'status_icon': '🟢',
            'status_class': 'status-online',
            'public_ip': '140.82.121.4',
            'location_display': 'Toruń, Kujawsko-Pomorskie, PL',
            'timezone': 'Europe/Warsaw',
            'provider': 'AS50599 DATASPACE P.S.A.',
            'dns_location': 'PL',
            'dns_server': 'WAW',
            'dns_status_icon': '✅',
            'minutes_ago': 2,
            'last_seen_relative': '2 minute(s) ago',
            'last_seen_formatted': '2025-10-13 20:45:59 UTC'
        }
    ],
    'total_clients': 1,
    'online_clients': 1,
    'offline_clients': 0,
    'current_time': '2025-10-13 20:47:59 UTC',
    'server_time': '2025-10-13 20:47:59 UTC',
    'dashboard_port': 5553,
    'server_info': {
        'public_ip': '172.67.163.127',
        'location': 'Madrid, Madrid, ES',
        'provider': 'AS57269 DIGI SPAIN TELECOM S.L.',
        'dns_status': 'Operational'
    }
}