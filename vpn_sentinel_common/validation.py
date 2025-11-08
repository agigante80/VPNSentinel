"""Input validation helpers migrated from vpn_sentinel_server.

These helpers are shared between server and client and therefore belong in
`vpn_sentinel_common` as the canonical implementation.
"""
from typing import Any
import re
import socket
from flask import request
from .logging import log_warn


def get_client_ip() -> str:
    """Extract the real client IP address from Flask request headers."""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr


def validate_client_id(client_id: Any) -> str:
    """Validate and sanitize client_id input."""
    if not isinstance(client_id, str):
        return 'unknown'

    client_id = client_id.strip()
    if len(client_id) > 100 or len(client_id) == 0:
        return 'unknown'

    if not re.match(r'^[a-zA-Z0-9._-]+$', client_id):
        return 'unknown'

    return client_id


def validate_public_ip(public_ip: Any) -> str:
    """Validate public IP address format (IPv4/IPv6)."""
    if not isinstance(public_ip, str):
        return 'unknown'
    public_ip = public_ip.strip()
    if len(public_ip) > 45 or len(public_ip) == 0:
        return 'unknown'

    try:
        socket.inet_pton(socket.AF_INET, public_ip)
        return public_ip
    except Exception:
        try:
            socket.inet_pton(socket.AF_INET6, public_ip)
            return public_ip
        except Exception:
            return 'unknown'


def validate_location_string(value: Any, field_name: str) -> str:
    """Validate and sanitize location-related string fields."""
    if not isinstance(value, str):
        return 'Unknown'

    value = value.strip()
    if len(value) > 100:
        return 'Unknown'

    allowed_pattern = r'^[a-zA-Z0-9\s.,\'"""\-]+$' if field_name != 'timezone' else r'^[a-zA-Z0-9\s.,\'"""\-/_]+$'
    # The above pattern intentionally permits common punctuation; fallback to Unknown on mismatch.
    try:
        if not re.match(allowed_pattern, value):
            log_warn('security', f'Potentially dangerous characters in {field_name}: {value}')
            return 'Unknown'
    except re.error:
        # In the unlikely event of a pattern error, return Unknown
        return 'Unknown'

    return value
