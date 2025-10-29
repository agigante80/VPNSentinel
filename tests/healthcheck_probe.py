#!/usr/bin/env python3
"""
Healthcheck probe used by docker-compose.test.yaml.
Attempts the dedicated health endpoint on 8081, then the API-mounted health endpoint
using VPN_SENTINEL_SERVER_API_PORT and VPN_SENTINEL_API_PATH environment variables.
Exits 0 on success, non-zero otherwise.
"""
import os
import sys
import requests

try:
    try:
        requests.get('http://localhost:8081/health', timeout=3).raise_for_status()
        print('ok:8081')
        sys.exit(0)
    except Exception:
        api_port = os.getenv('VPN_SENTINEL_SERVER_API_PORT', '5000')
        api_path = os.getenv('VPN_SENTINEL_API_PATH', '/api/v1')
        url = f'http://localhost:{api_port}{api_path}/health'
        requests.get(url, timeout=3).raise_for_status()
        print(f'ok:{url}')
        sys.exit(0)
except Exception as e:
    print('healthcheck failed:', e)
    sys.exit(1)
