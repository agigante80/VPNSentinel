"""Tests for DNS leak detection functionality.

This module tests the complete DNS leak detection flow including:
- Cloudflare DNS trace parsing (dig output)
- HTTP fallback trace parsing
- Integration with keepalive payload
"""
import pytest
from unittest.mock import patch, Mock
from vpn_sentinel_common.network import parse_dns_trace


class TestParseDnsTrace:
    """Test DNS trace parsing with various formats."""

    def test_parse_cloudflare_quoted_format(self):
        """Test parsing Cloudflare's quoted single-line format."""
        trace = '"fl=195f311 h=whoami.cloudflare ip=1.2.3.4 ts=1234567890.123 loc=US colo=SJC"'
        result = parse_dns_trace(trace)
        assert result['loc'] == 'US'
        assert result['colo'] == 'SJC'

    def test_parse_cloudflare_unquoted_format(self):
        """Test parsing Cloudflare's unquoted single-line format."""
        trace = 'fl=195f311 h=whoami.cloudflare ip=1.2.3.4 ts=1234567890.123 loc=PL colo=WAW'
        result = parse_dns_trace(trace)
        assert result['loc'] == 'PL'
        assert result['colo'] == 'WAW'

    def test_parse_cloudflare_http_trace(self):
        """Test parsing Cloudflare HTTP /cdn-cgi/trace response."""
        trace = """fl=195f311
h=www.cloudflare.com
ip=203.0.113.42
ts=1234567890.123
visit_scheme=https
uag=curl/7.68.0
colo=MAD
sliver=none
http=http/2
loc=ES
tls=TLSv1.3
sni=plaintext
warp=off
gateway=off"""
        result = parse_dns_trace(trace)
        assert result['loc'] == 'ES'
        assert result['colo'] == 'MAD'

    def test_parse_multiline_format(self):
        """Test parsing legacy multiline format."""
        trace = """loc=GB
colo=LHR"""
        result = parse_dns_trace(trace)
        assert result['loc'] == 'GB'
        assert result['colo'] == 'LHR'

    def test_parse_partial_data(self):
        """Test parsing when only one field is present."""
        trace = 'loc=FR colo='
        result = parse_dns_trace(trace)
        assert result['loc'] == 'FR'
        assert result['colo'] == ''

        trace2 = 'loc= colo=CDG'
        result2 = parse_dns_trace(trace2)
        assert result2['loc'] == ''
        assert result2['colo'] == 'CDG'

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        result = parse_dns_trace('')
        assert result['loc'] == ''
        assert result['colo'] == ''

    def test_parse_invalid_format(self):
        """Test parsing invalid/malformed data."""
        trace = 'this is not valid trace data'
        result = parse_dns_trace(trace)
        assert result['loc'] == ''
        assert result['colo'] == ''

    def test_parse_with_extra_fields(self):
        """Test parsing ignores extra fields."""
        trace = 'fl=123 loc=DE colo=FRA ip=1.2.3.4 extra=field'
        result = parse_dns_trace(trace)
        assert result['loc'] == 'DE'
        assert result['colo'] == 'FRA'

    def test_parse_with_whitespace(self):
        """Test parsing handles extra whitespace."""
        trace = '  loc=IT   colo=MXP  '
        result = parse_dns_trace(trace)
        assert result['loc'] == 'IT'
        assert result['colo'] == 'MXP'

    def test_parse_country_codes(self):
        """Test parsing various country codes."""
        test_cases = [
            ('loc=US colo=LAX', 'US', 'LAX'),
            ('loc=GB colo=LHR', 'GB', 'LHR'),
            ('loc=JP colo=NRT', 'JP', 'NRT'),
            ('loc=AU colo=SYD', 'AU', 'SYD'),
            ('loc=BR colo=GRU', 'BR', 'GRU'),
        ]
        for trace, expected_loc, expected_colo in test_cases:
            result = parse_dns_trace(trace)
            assert result['loc'] == expected_loc, f"Failed for trace: {trace}"
            assert result['colo'] == expected_colo, f"Failed for trace: {trace}"


# Note: The following tests for get_dns_info and send_keepalive functions
# are skipped because vpn-sentinel-client.py is not a Python module.
# The parse_dns_trace tests above provide coverage for the core DNS parsing logic.
# Integration tests in tests/integration/ cover the complete keepalive flow.


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
