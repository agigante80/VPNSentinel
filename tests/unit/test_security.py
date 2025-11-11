"""
Unit tests for Security module (security.py)
Tests rate limiting, IP whitelisting, access logging, and middleware.
"""
import pytest
import time
import sys
import os

# Add common library to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from vpn_sentinel_common import security


class TestRateLimiting:
    """Tests for check_rate_limit function."""
    
    def setup_method(self):
        """Clear rate limit storage before each test."""
        security.rate_limit_storage.clear()
    
    def test_rate_limit_allows_initial_requests(self):
        """Test initial requests under limit are allowed."""
        for i in range(security.RATE_LIMIT_REQUESTS):
            assert security.check_rate_limit('1.2.3.4') is True
    
    def test_rate_limit_blocks_excess_requests(self):
        """Test requests over limit are blocked."""
        # Fill up to the limit
        for i in range(security.RATE_LIMIT_REQUESTS):
            security.check_rate_limit('1.2.3.4')
        
        # Next request should be blocked
        assert security.check_rate_limit('1.2.3.4') is False
    
    def test_rate_limit_per_ip(self):
        """Test rate limiting is per IP address."""
        # Fill limit for IP 1
        for i in range(security.RATE_LIMIT_REQUESTS):
            security.check_rate_limit('1.2.3.4')
        
        # IP 2 should still be allowed
        assert security.check_rate_limit('5.6.7.8') is True
    
    def test_rate_limit_sliding_window(self):
        """Test sliding window drops old requests."""
        # Fill up the limit
        for i in range(security.RATE_LIMIT_REQUESTS):
            security.check_rate_limit('1.2.3.4')
        
        # Should be blocked now
        assert security.check_rate_limit('1.2.3.4') is False
        
        # Manually age out old requests
        old_time = time.time() - security.RATE_LIMIT_WINDOW - 1
        security.rate_limit_storage['1.2.3.4'].clear()
        security.rate_limit_storage['1.2.3.4'].append(old_time)
        
        # Should be allowed again
        assert security.check_rate_limit('1.2.3.4') is True
    
    def test_rate_limit_constants(self):
        """Test rate limit constants are sensible."""
        assert security.RATE_LIMIT_REQUESTS > 0
        assert security.RATE_LIMIT_WINDOW > 0


class TestIpWhitelist:
    """Tests for check_ip_whitelist function."""
    
    def setup_method(self):
        """Reset whitelist before each test."""
        security.ALLOWED_IPS.clear()
    
    def test_whitelist_empty_allows_all(self):
        """Test empty whitelist allows all IPs."""
        assert security.check_ip_whitelist('1.2.3.4') is True
        assert security.check_ip_whitelist('5.6.7.8') is True
    
    def test_whitelist_allows_listed_ips(self):
        """Test whitelist allows listed IPs."""
        security.ALLOWED_IPS.extend(['1.2.3.4', '5.6.7.8'])
        
        assert security.check_ip_whitelist('1.2.3.4') is True
        assert security.check_ip_whitelist('5.6.7.8') is True
    
    def test_whitelist_blocks_unlisted_ips(self):
        """Test whitelist blocks unlisted IPs."""
        security.ALLOWED_IPS.extend(['1.2.3.4'])
        
        assert security.check_ip_whitelist('5.6.7.8') is False
        assert security.check_ip_whitelist('9.10.11.12') is False
    
    def test_whitelist_exact_match(self):
        """Test whitelist uses exact string matching."""
        security.ALLOWED_IPS.extend(['1.2.3.4'])
        
        # Exact match
        assert security.check_ip_whitelist('1.2.3.4') is True
        
        # Partial matches should not work
        assert security.check_ip_whitelist('1.2.3.') is False
        assert security.check_ip_whitelist('1.2.3.40') is False


class TestLogAccess:
    """Tests for log_access function."""
    
    def test_log_access_accepts_flexible_args(self):
        """Test log_access accepts various arguments without error."""
        # Should not raise any exceptions
        security.log_access()
        security.log_access('event')
        security.log_access('event', '1.2.3.4')
        security.log_access('event', '1.2.3.4', 'user-agent', 'extra', 200)
    
    def test_log_access_returns_none(self):
        """Test log_access returns None."""
        result = security.log_access('event', '1.2.3.4')
        assert result is None
    
    def test_log_access_accepts_kwargs(self):
        """Test log_access accepts keyword arguments."""
        # Should not raise
        security.log_access(event='test', ip='1.2.3.4', code=200)


class TestSecurityMiddleware:
    """Tests for security_middleware function."""
    
    def test_security_middleware_returns_callable(self):
        """Test security_middleware returns a callable."""
        middleware = security.security_middleware()
        assert callable(middleware)
    
    def test_security_middleware_callable_returns_none(self):
        """Test middleware callable returns None."""
        middleware = security.security_middleware()
        result = middleware()
        assert result is None
    
    def test_security_middleware_factory_pattern(self):
        """Test security_middleware follows factory pattern."""
        middleware1 = security.security_middleware()
        middleware2 = security.security_middleware()
        
        # Each call should return a new function
        assert middleware1 is not middleware2
        
        # But they should behave the same
        assert middleware1() is None
        assert middleware2() is None
