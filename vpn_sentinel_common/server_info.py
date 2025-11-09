"""Server information helpers (public IP, geolocation, DNS checks).

Migrated from `vpn_sentinel_server.server_info` as a shared implementation so
both server and client tooling can reuse the canonical code.
"""
import requests
from typing import Dict
from .log_utils import log_info, log_warn, log_error


def get_server_public_ip() -> str:
    """Return server public IP using ipinfo.io or ipify as fallback."""
    try:
        response = requests.get('https://ipinfo.io/json', timeout=10, verify=True)
        if response.status_code == 200:
            data = response.json()
            return data.get('ip', 'Unknown')
    except Exception:
        pass

    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=10, verify=True)
        if response.status_code == 200:
            data = response.json()
            return data.get('ip', 'Unknown')
    except Exception:
        pass

    return 'Unknown'


def get_server_info() -> Dict[str, str]:
    """Return a dict with public_ip, location, provider, dns_status.

    Uses ipinfo.io and falls back to ip-api.com. Errors are logged.
    """
    server_info = {
        'public_ip': 'Unknown',
        'location': 'Unknown',
        'provider': 'Unknown',
        'dns_status': 'Unknown',
    }

    try:
        response = requests.get('https://ipinfo.io/json', timeout=10)
        geolocation_source = 'ipinfo.io'

        if response.status_code != 200:
            log_warn('server_info', 'Primary geolocation service failed; trying fallback')
            response = requests.get('http://ip-api.com/json', timeout=10)
            geolocation_source = 'ip-api.com'

            if response.status_code != 200:
                raise Exception('Both geolocation services failed')

        data = response.json()
        log_info('server_info', f'📡 Server geolocation from: {geolocation_source}')

        if geolocation_source == 'ip-api.com':
            server_info['public_ip'] = data.get('query', 'Unknown')
            city = data.get('city', '')
            region = data.get('regionName', '')
            country = data.get('countryCode', 'Unknown')
            if city and region:
                server_info['location'] = f"{city}, {region}, {country}"
            elif city:
                server_info['location'] = f"{city}, {country}"
            else:
                server_info['location'] = country
            server_info['provider'] = data.get('isp', 'Unknown Provider')
        else:
            server_info['public_ip'] = data.get('ip', 'Unknown')
            city = data.get('city', '')
            region = data.get('region', '')
            country = data.get('country', 'Unknown')
            if city and region:
                server_info['location'] = f"{city}, {region}, {country}"
            elif city:
                server_info['location'] = f"{city}, {country}"
            else:
                server_info['location'] = country
            server_info['provider'] = data.get('org', 'Unknown Provider')

        try:
            import socket
            socket.gethostbyname('google.com')
            server_info['dns_status'] = 'Operational'
        except Exception:
            server_info['dns_status'] = 'Issues Detected'

    except Exception as e:
        log_error('server_info', f'Failed to get server information: {e}')

    return server_info
