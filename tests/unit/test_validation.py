"""Unit tests for vpn_sentinel_common.validation module.

Tests input validation and sanitization functions.
"""
import pytest
import socket
from unittest.mock import patch, MagicMock
from flask import Flask
from vpn_sentinel_common.validation import (
    get_client_ip,
    validate_client_id,
    validate_public_ip,
    validate_location_string
)


@pytest.fixture
def app():
    """Create Flask app for request context."""
    app = Flask(__name__)
    return app


class TestGetClientIp:
    """Tests for get_client_ip() function."""

    def test_get_client_ip_x_forwarded_for(self, app):
        """Test getting IP from X-Forwarded-For header."""
        with app.test_request_context(headers={'X-Forwarded-For': '203.0.113.1, 198.51.100.1'}):
            ip = get_client_ip()
            assert ip == '203.0.113.1'

    def test_get_client_ip_x_forwarded_for_single(self, app):
        """Test getting IP from X-Forwarded-For with single IP."""
        with app.test_request_context(headers={'X-Forwarded-For': '203.0.113.42'}):
            ip = get_client_ip()
            assert ip == '203.0.113.42'

    def test_get_client_ip_x_real_ip(self, app):
        """Test getting IP from X-Real-IP header."""
        with app.test_request_context(headers={'X-Real-IP': '192.0.2.100'}):
            ip = get_client_ip()
            assert ip == '192.0.2.100'

    def test_get_client_ip_remote_addr(self, app):
        """Test getting IP from remote_addr when no headers present."""
        with app.test_request_context(environ_base={'REMOTE_ADDR': '198.51.100.50'}):
            ip = get_client_ip()
            assert ip == '198.51.100.50'

    def test_get_client_ip_priority_x_forwarded_for(self, app):
        """Test X-Forwarded-For takes priority over X-Real-IP."""
        with app.test_request_context(headers={
            'X-Forwarded-For': '203.0.113.1',
            'X-Real-IP': '192.0.2.100'
        }):
            ip = get_client_ip()
            assert ip == '203.0.113.1'

    def test_get_client_ip_whitespace_handling(self, app):
        """Test whitespace is stripped from X-Forwarded-For."""
        with app.test_request_context(headers={'X-Forwarded-For': '  203.0.113.1  ,  198.51.100.1  '}):
            ip = get_client_ip()
            assert ip == '203.0.113.1'


class TestValidateClientId:
    """Tests for validate_client_id() function."""

    def test_validate_client_id_valid(self):
        """Test valid client IDs are accepted."""
        valid_ids = [
            'client-123',
            'office_vpn',
            'home.router',
            'test_client-1.2',
            'a1b2c3'
        ]
        for client_id in valid_ids:
            result = validate_client_id(client_id)
            assert result == client_id

    def test_validate_client_id_strips_whitespace(self):
        """Test client ID whitespace is stripped."""
        result = validate_client_id('  client-123  ')
        assert result == 'client-123'

    def test_validate_client_id_empty_string(self):
        """Test empty string returns unknown."""
        result = validate_client_id('')
        assert result == 'unknown'

    def test_validate_client_id_only_whitespace(self):
        """Test whitespace-only string returns unknown."""
        result = validate_client_id('   ')
        assert result == 'unknown'

    def test_validate_client_id_too_long(self):
        """Test client ID over 100 chars returns unknown."""
        long_id = 'a' * 101
        result = validate_client_id(long_id)
        assert result == 'unknown'

    def test_validate_client_id_exactly_100_chars(self):
        """Test client ID exactly 100 chars is accepted."""
        id_100 = 'a' * 100
        result = validate_client_id(id_100)
        assert result == id_100

    def test_validate_client_id_invalid_characters(self):
        """Test client IDs with invalid characters return unknown."""
        invalid_ids = [
            'client@123',
            'test client',
            'client#1',
            'client$vpn',
            'test%',
            'client/vpn',
            'test\\client',
            'client;drop'
        ]
        for client_id in invalid_ids:
            result = validate_client_id(client_id)
            assert result == 'unknown', f"Expected 'unknown' for {client_id}"

    def test_validate_client_id_not_string(self):
        """Test non-string types return unknown."""
        invalid_types = [
            123,
            None,
            ['client'],
            {'id': 'client'},
            12.34
        ]
        for value in invalid_types:
            result = validate_client_id(value)
            assert result == 'unknown'


class TestValidatePublicIp:
    """Tests for validate_public_ip() function."""

    def test_validate_public_ip_valid_ipv4(self):
        """Test valid IPv4 addresses are accepted."""
        valid_ips = [
            '192.168.1.1',
            '8.8.8.8',
            '203.0.113.42',
            '0.0.0.0',
            '255.255.255.255'
        ]
        for ip in valid_ips:
            result = validate_public_ip(ip)
            assert result == ip

    def test_validate_public_ip_valid_ipv6(self):
        """Test valid IPv6 addresses are accepted."""
        valid_ips = [
            '2001:0db8:85a3:0000:0000:8a2e:0370:7334',
            '::1',
            'fe80::1',
            '::',
            '2001:db8::1'
        ]
        for ip in valid_ips:
            result = validate_public_ip(ip)
            assert result == ip

    def test_validate_public_ip_strips_whitespace(self):
        """Test IP whitespace is stripped."""
        result = validate_public_ip('  192.168.1.1  ')
        assert result == '192.168.1.1'

    def test_validate_public_ip_invalid_format(self):
        """Test invalid IP formats return unknown."""
        invalid_ips = [
            '999.999.999.999',
            '192.168.1',
            '192.168.1.1.1',
            'not-an-ip',
            '192.168.1.256',
            'gggg::1'
        ]
        for ip in invalid_ips:
            result = validate_public_ip(ip)
            assert result == 'unknown', f"Expected 'unknown' for {ip}"

    def test_validate_public_ip_empty_string(self):
        """Test empty string returns unknown."""
        result = validate_public_ip('')
        assert result == 'unknown'

    def test_validate_public_ip_too_long(self):
        """Test IP over 45 chars returns unknown."""
        long_ip = 'a' * 46
        result = validate_public_ip(long_ip)
        assert result == 'unknown'

    def test_validate_public_ip_not_string(self):
        """Test non-string types return unknown."""
        invalid_types = [
            123,
            None,
            ['192.168.1.1'],
            {'ip': '192.168.1.1'}
        ]
        for value in invalid_types:
            result = validate_public_ip(value)
            assert result == 'unknown'


class TestValidateLocationString:
    """Tests for validate_location_string() function."""

    def test_validate_location_string_valid(self):
        """Test valid location strings are accepted."""
        valid_strings = [
            ('United States', 'country'),
            ('San Francisco', 'city'),
            ('California', 'region'),
            ("O'Reilly", 'city'),
            ('AS15169 Google LLC', 'org')
        ]
        for value, field_name in valid_strings:
            result = validate_location_string(value, field_name)
            assert result == value
    
    def test_validate_location_string_non_ascii(self):
        """Test non-ASCII characters are rejected."""
        # The regex pattern only allows ASCII characters
        with patch('vpn_sentinel_common.validation.log_warn'):
            result = validate_location_string('São Paulo', 'city')
            assert result == 'Unknown'

    def test_validate_location_string_timezone(self):
        """Test timezone strings with slashes are accepted."""
        timezones = [
            'America/Los_Angeles',
            'Europe/London',
            'Asia/Tokyo',
            'UTC',
            'America/New_York'
        ]
        for tz in timezones:
            result = validate_location_string(tz, 'timezone')
            assert result == tz

    def test_validate_location_string_strips_whitespace(self):
        """Test location string whitespace is stripped."""
        result = validate_location_string('  United States  ', 'country')
        assert result == 'United States'

    def test_validate_location_string_empty(self):
        """Test empty string returns Unknown."""
        result = validate_location_string('', 'city')
        assert result == 'Unknown'

    def test_validate_location_string_too_long(self):
        """Test string over 100 chars returns Unknown."""
        long_string = 'a' * 101
        result = validate_location_string(long_string, 'city')
        assert result == 'Unknown'

    def test_validate_location_string_exactly_100_chars(self):
        """Test string exactly 100 chars is accepted."""
        string_100 = 'a' * 100
        result = validate_location_string(string_100, 'city')
        assert result == string_100

    def test_validate_location_string_invalid_characters(self):
        """Test strings with dangerous characters return Unknown."""
        invalid_strings = [
            ('Test<script>', 'city'),
            ('Location; DROP TABLE', 'region'),
            ('City & Hacked', 'city'),
            ('Test@Location', 'org'),
            ('City$Money', 'city')
        ]
        with patch('vpn_sentinel_common.validation.log_warn') as mock_warn:
            for value, field_name in invalid_strings:
                result = validate_location_string(value, field_name)
                assert result == 'Unknown', f"Expected 'Unknown' for {value}"
            
            # Verify warnings were logged
            assert mock_warn.called

    def test_validate_location_string_slash_not_in_timezone(self):
        """Test slash is rejected in non-timezone fields."""
        with patch('vpn_sentinel_common.validation.log_warn') as mock_warn:
            result = validate_location_string('City/Region', 'city')
            assert result == 'Unknown'
            mock_warn.assert_called_once()

    def test_validate_location_string_not_string(self):
        """Test non-string types return Unknown."""
        invalid_types = [
            123,
            None,
            ['City'],
            {'city': 'London'}
        ]
        for value in invalid_types:
            result = validate_location_string(value, 'city')
            assert result == 'Unknown'

    def test_validate_location_string_regex_error(self):
        """Test regex error handling returns Unknown."""
        # Mock re.match to raise re.error (which is caught in the code)
        import re
        with patch('vpn_sentinel_common.validation.re.match', side_effect=re.error('Pattern error')):
            result = validate_location_string('Test', 'city')
            assert result == 'Unknown'


class TestValidationIntegration:
    """Integration tests for validation module."""

    def test_validate_all_functions_with_none(self):
        """Test all validation functions handle None gracefully."""
        assert validate_client_id(None) == 'unknown'
        assert validate_public_ip(None) == 'unknown'
        assert validate_location_string(None, 'city') == 'Unknown'

    def test_validate_chained_sanitization(self):
        """Test validation functions can be chained."""
        client_id = validate_client_id('  test-client  ')
        ip = validate_public_ip('  192.168.1.1  ')
        location = validate_location_string('  United States  ', 'country')
        
        assert client_id == 'test-client'
        assert ip == '192.168.1.1'
        assert location == 'United States'

    def test_security_injection_attempts(self):
        """Test validation blocks common injection attempts."""
        with patch('vpn_sentinel_common.validation.log_warn'):
            # SQL injection attempts
            assert validate_location_string("'; DROP TABLE users; --", 'city') == 'Unknown'
            
            # XSS attempts
            assert validate_location_string('<script>alert("xss")</script>', 'city') == 'Unknown'
            
            # Command injection
            assert validate_location_string('City | rm -rf /', 'city') == 'Unknown'
