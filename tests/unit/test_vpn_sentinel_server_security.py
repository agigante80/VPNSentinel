from vpn_sentinel_server import security
from flask import Flask


def test_check_rate_limit_allows_requests_under_limit():
    ip = '1.2.3.4'
    # Reset storage for test isolation
    security.rate_limit_storage.pop(ip, None)
    # Allow RATE_LIMIT_REQUESTS requests
    allowed = True
    for _ in range(0, security.RATE_LIMIT_REQUESTS):
        if not security.check_rate_limit(ip):
            allowed = False
            break
    assert allowed


def test_check_rate_limit_blocks_after_limit():
    ip = '5.6.7.8'
    security.rate_limit_storage.pop(ip, None)
    for _ in range(0, security.RATE_LIMIT_REQUESTS):
        security.check_rate_limit(ip)
    assert not security.check_rate_limit(ip)


def test_check_ip_whitelist_allows_when_empty():
    # Ensure ALLOWED_IPS empty scenario returns True
    orig = security.ALLOWED_IPS
    security.ALLOWED_IPS = []
    assert security.check_ip_whitelist('1.1.1.1') is True
    security.ALLOWED_IPS = orig


def test_check_ip_whitelist_respects_list():
    orig = security.ALLOWED_IPS
    security.ALLOWED_IPS = ['9.9.9.9']
    assert security.check_ip_whitelist('9.9.9.9') is True
    assert security.check_ip_whitelist('8.8.8.8') is False
    security.ALLOWED_IPS = orig
