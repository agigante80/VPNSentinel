"""Unit tests for vpn_sentinel_common.network module.

Tests network helper functions including geolocation parsing and DNS trace parsing.
"""
import pytest
from vpn_sentinel_common.network import parse_geolocation, parse_dns_trace


class TestParseGeolocation:
    """Tests for parse_geolocation() function."""

    def test_parse_geolocation_ipinfo_format(self):
        """Test parsing ipinfo.io JSON format."""
        json_text = '''
        {
            "ip": "8.8.8.8",
            "country": "US",
            "city": "Mountain View",
            "region": "California",
            "org": "AS15169 Google LLC",
            "timezone": "America/Los_Angeles"
        }
        '''
        result = parse_geolocation(json_text, source="ipinfo.io")
        
        assert result['ip'] == '8.8.8.8'
        assert result['country'] == 'US'
        assert result['city'] == 'Mountain View'
        assert result['region'] == 'California'
        assert result['org'] == 'AS15169 Google LLC'
        assert result['timezone'] == 'America/Los_Angeles'

    def test_parse_geolocation_ip_api_format(self):
        """Test parsing ip-api.com JSON format."""
        json_text = '''
        {
            "query": "1.2.3.4",
            "countryCode": "GB",
            "city": "London",
            "regionName": "England",
            "isp": "British Telecom",
            "timezone": "Europe/London"
        }
        '''
        result = parse_geolocation(json_text, source="ip-api.com")
        
        assert result['ip'] == '1.2.3.4'
        assert result['country'] == 'GB'
        assert result['city'] == 'London'
        assert result['region'] == 'England'
        assert result['org'] == 'British Telecom'
        assert result['timezone'] == 'Europe/London'

    def test_parse_geolocation_invalid_json(self):
        """Test parsing invalid JSON returns empty fields."""
        json_text = 'not valid json {'
        result = parse_geolocation(json_text)
        
        assert result['ip'] == ''
        assert result['country'] == ''
        assert result['city'] == ''
        assert result['region'] == ''
        assert result['org'] == ''
        assert result['timezone'] == ''

    def test_parse_geolocation_empty_string(self):
        """Test parsing empty string returns empty fields."""
        result = parse_geolocation('')
        
        assert result['ip'] == ''
        assert result['country'] == ''
        assert result['city'] == ''
        assert result['region'] == ''
        assert result['org'] == ''
        assert result['timezone'] == ''

    def test_parse_geolocation_missing_fields_ipinfo(self):
        """Test ipinfo format with missing fields returns empty strings."""
        json_text = '{"ip": "5.5.5.5"}'
        result = parse_geolocation(json_text, source="ipinfo.io")
        
        assert result['ip'] == '5.5.5.5'
        assert result['country'] == ''
        assert result['city'] == ''
        assert result['region'] == ''
        assert result['org'] == ''
        assert result['timezone'] == ''

    def test_parse_geolocation_missing_fields_ip_api(self):
        """Test ip-api format with missing fields returns empty strings."""
        json_text = '{"query": "6.6.6.6", "countryCode": "FR"}'
        result = parse_geolocation(json_text, source="ip-api.com")
        
        assert result['ip'] == '6.6.6.6'
        assert result['country'] == 'FR'
        assert result['city'] == ''
        assert result['region'] == ''
        assert result['org'] == ''
        assert result['timezone'] == ''

    def test_parse_geolocation_null_values_ipinfo(self):
        """Test ipinfo format with null values returns empty strings."""
        json_text = '{"ip": null, "country": null, "city": null}'
        result = parse_geolocation(json_text, source="ipinfo.io")
        
        # null values should be converted to empty strings
        assert result['ip'] == ''
        assert result['country'] == ''
        assert result['city'] == ''

    def test_parse_geolocation_null_values_ip_api(self):
        """Test ip-api format with null values returns empty strings."""
        json_text = '{"query": null, "countryCode": "DE", "city": null}'
        result = parse_geolocation(json_text, source="ip-api.com")
        
        assert result['ip'] == ''
        assert result['country'] == 'DE'
        assert result['city'] == ''

    def test_parse_geolocation_default_source(self):
        """Test default source is ipinfo.io."""
        json_text = '{"ip": "7.7.7.7", "country": "CA"}'
        result = parse_geolocation(json_text)  # No source specified
        
        # Should use ipinfo format (country not countryCode)
        assert result['ip'] == '7.7.7.7'
        assert result['country'] == 'CA'


class TestParseDnsTrace:
    """Tests for parse_dns_trace() function."""

    def test_parse_dns_trace_cloudflare_format(self):
        """Test parsing Cloudflare's quoted space-separated format."""
        trace = 'fl="195f311" h="one.one.one.one" ip="203.0.113.1" ts="1234567890" loc=US colo=SJC'
        result = parse_dns_trace(trace)
        
        assert result['loc'] == 'US'
        assert result['colo'] == 'SJC'

    def test_parse_dns_trace_quoted_string(self):
        """Test parsing when trace text is in quotes."""
        trace = '"loc=GB colo=LHR"'
        result = parse_dns_trace(trace)
        
        assert result['loc'] == 'GB'
        assert result['colo'] == 'LHR'

    def test_parse_dns_trace_multiline_format(self):
        """Test parsing multiline format."""
        trace = 'loc=FR\ncolo=CDG'
        result = parse_dns_trace(trace)
        
        assert result['loc'] == 'FR'
        assert result['colo'] == 'CDG'

    def test_parse_dns_trace_only_loc(self):
        """Test parsing with only location field."""
        trace = 'loc=JP'
        result = parse_dns_trace(trace)
        
        assert result['loc'] == 'JP'
        assert result['colo'] == ''

    def test_parse_dns_trace_only_colo(self):
        """Test parsing with only colo field."""
        trace = 'colo=NRT'
        result = parse_dns_trace(trace)
        
        assert result['loc'] == ''
        assert result['colo'] == 'NRT'

    def test_parse_dns_trace_empty_string(self):
        """Test parsing empty string returns empty fields."""
        result = parse_dns_trace('')
        
        assert result['loc'] == ''
        assert result['colo'] == ''

    def test_parse_dns_trace_no_relevant_fields(self):
        """Test parsing trace with no loc or colo fields."""
        trace = 'fl="test" ip="1.2.3.4" ts="12345"'
        result = parse_dns_trace(trace)
        
        assert result['loc'] == ''
        assert result['colo'] == ''

    def test_parse_dns_trace_mixed_format(self):
        """Test parsing trace with multiple loc/colo pairs."""
        # split() splits on all whitespace, so all loc= and colo= pairs
        # are processed. Last value wins.
        trace = 'loc=US colo=SJC\nloc=GB\ncolo=LHR'
        result = parse_dns_trace(trace)
        
        # Last values in the sequence win
        assert result['loc'] == 'GB'
        assert result['colo'] == 'LHR'

    def test_parse_dns_trace_multiline_fallback(self):
        """Test multiline parsing when space-separated doesn't have fields."""
        # No space-separated loc/colo, should fall back to multiline
        trace = 'fl="test"\nloc=AU\ncolo=SYD'
        result = parse_dns_trace(trace)
        
        assert result['loc'] == 'AU'
        assert result['colo'] == 'SYD'

    def test_parse_dns_trace_value_with_equals(self):
        """Test parsing when value contains equals sign."""
        trace = 'loc=US=TEST colo=SJC'
        result = parse_dns_trace(trace)
        
        # Should split on first = only
        assert result['loc'] == 'US=TEST'
        assert result['colo'] == 'SJC'

    def test_parse_dns_trace_whitespace(self):
        """Test parsing handles extra whitespace."""
        trace = '  loc=NL   colo=AMS  '
        result = parse_dns_trace(trace)
        
        assert result['loc'] == 'NL'
        assert result['colo'] == 'AMS'

    def test_parse_dns_trace_complex_cloudflare_response(self):
        """Test parsing complex real-world Cloudflare response."""
        trace = '"fl=195f311 h=one.one.one.one ip=203.0.113.42 ts=1699721234.567 visit_scheme=https uag=curl/7.68.0 colo=SEA sliver=none http=http/2 loc=US tls=TLSv1.3 sni=plaintext warp=off gateway=off rbi=off kex=X25519"'
        result = parse_dns_trace(trace)
        
        assert result['loc'] == 'US'
        assert result['colo'] == 'SEA'


class TestNetworkIntegration:
    """Integration tests for network module."""

    def test_parse_geolocation_all_sources(self):
        """Test parsing works for all supported sources."""
        sources = ["ipinfo.io", "ip-api.com"]
        
        for source in sources:
            if source == "ipinfo.io":
                json_text = '{"ip": "1.1.1.1", "country": "US"}'
            else:
                json_text = '{"query": "1.1.1.1", "countryCode": "US"}'
            
            result = parse_geolocation(json_text, source=source)
            assert result['ip'] == '1.1.1.1'
            assert result['country'] == 'US'

    def test_dns_trace_format_compatibility(self):
        """Test DNS trace parsing handles both old and new formats."""
        # New format (space-separated)
        new_format = 'loc=US colo=SJC'
        result1 = parse_dns_trace(new_format)
        
        # Old format (multiline)
        old_format = 'loc=US\ncolo=SJC'
        result2 = parse_dns_trace(old_format)
        
        # Both should produce same result
        assert result1['loc'] == result2['loc']
        assert result1['colo'] == result2['colo']
