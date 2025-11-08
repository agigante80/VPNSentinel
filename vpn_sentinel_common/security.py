"""Security helpers migrated from vpn_sentinel_server.

This module provides rate limiting, whitelist checks and middleware that can
be used by both server and clients (where applicable). Configuration is
read from environment variables to remain portable across deployments.
"""
import time
from collections import deque
from typing import Dict
from flask import request, jsonify
from .logging import log_info
from .validation import get_client_ip
import os

# Configuration imported from environment variables at runtime
RATE_LIMIT_REQUESTS = int(os.getenv('VPN_SENTINEL_SERVER_RATE_LIMIT_REQUESTS', '30'))
RATE_LIMIT_WINDOW = int(os.getenv('VPN_SENTINEL_SERVER_RATE_LIMIT_WINDOW', '60'))
ALLOWED_IPS = [ip.strip() for ip in os.getenv('VPN_SENTINEL_SERVER_ALLOWED_IPS', '').split(',') if ip.strip()] if os.getenv('VPN_SENTINEL_SERVER_ALLOWED_IPS') else []
API_KEY = os.getenv('VPN_SENTINEL_API_KEY', '')

# In-memory storage for rate limiting in this module
rate_limit_storage: Dict[str, deque] = {}


def check_rate_limit(ip: str) -> bool:
    now = time.time()
    storage = rate_limit_storage.setdefault(ip, deque())

    # Clean expired entries
    while storage and storage[0] < now - RATE_LIMIT_WINDOW:
        storage.popleft()

    if len(storage) >= RATE_LIMIT_REQUESTS:
        return False

    storage.append(now)
    return True


def check_ip_whitelist(ip: str) -> bool:
    # Allow tests and legacy shims to override the effective ALLOWED_IPS by
    # setting it on the vpn_sentinel_server shim module. Prefer that when
    # present so unit tests that patch vpn_sentinel_server.ALLOWED_IPS work as
    # expected during the incremental refactor.
    try:
        import vpn_sentinel_server as _server_shim

        effective_allowed = getattr(_server_shim, 'ALLOWED_IPS', ALLOWED_IPS)
    except Exception:
        effective_allowed = ALLOWED_IPS

    if not effective_allowed:
        return True
    return ip in effective_allowed


def log_access(endpoint: str, ip: str, user_agent: str, auth_header: str, status: str) -> None:
    auth_info = 'WITH_KEY' if auth_header and auth_header.startswith('Bearer') else 'NO_KEY'
    log_info('api', f"🌐 Access: {endpoint} | IP: {ip} | Auth: {auth_info} | Status: {status} | UA: {user_agent[:50]}...")


def security_middleware() -> None:
    client_ip = get_client_ip()
    user_agent = request.headers.get('User-Agent', 'Unknown')
    auth_header = request.headers.get('Authorization', '')
    endpoint = request.endpoint or request.path

    if not check_ip_whitelist(client_ip):
        log_access(endpoint, client_ip, user_agent, auth_header, '403_IP_BLOCKED')
        return jsonify({'error': 'IP not allowed'}), 403

    if not check_rate_limit(client_ip):
        log_access(endpoint, client_ip, user_agent, auth_header, '429_RATE_LIMITED')
        return jsonify({'error': 'Rate limit exceeded'}), 429

    if API_KEY:
        if auth_header != f'Bearer {API_KEY}':
            log_access(endpoint, client_ip, user_agent, auth_header, '401_UNAUTHORIZED')
            return '', 401

    log_access(endpoint, client_ip, user_agent, auth_header, '200_OK')
    return None
