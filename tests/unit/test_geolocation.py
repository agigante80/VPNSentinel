"""
Unit tests for Geolocation module (geolocation.py)
Tests geolocation API calls, parsing, and fallback logic.
"""
import pytest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add common library to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from vpn_sentinel_common.geolocation import (
    get_geolocation,
    _http_get,
    _parse_ipinfo,
    _parse_ip_api,
    _parse_ipwhois
)


class TestHttpGet:
    """Tests for _http_get helper function."""
    
    @patch('vpn_sentinel_common.geolocation.requests')
    def test_http_get_success_with_requests(self, mock_requests):
        """Test successful HTTP GET with requests library."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"ip": "1.2.3.4"}'
        mock_requests.get.return_value = mock_response
        
        result = _http_get('https://ipinfo.io/json', 5)
        
        assert result == '{"ip": "1.2.3.4"}'
        mock_requests.get.assert_called_once_with('https://ipinfo.io/json', timeout=5)
    
    @patch('vpn_sentinel_common.geolocation.requests')
    def test_http_get_non_200_status(self, mock_requests):
        """Test HTTP GET with non-200 status code."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_requests.get.return_value = mock_response
        
        result = _http_get('https://example.com', 5)
        
        assert result is None
    
    @patch('vpn_sentinel_common.geolocation.requests')
    def test_http_get_exception(self, mock_requests):
        """Test HTTP GET handles exceptions."""
        mock_requests.get.side_effect = Exception("Network error")
        
        result = _http_get('https://example.com', 5)
        
        assert result is None
    
    @patch('vpn_sentinel_common.geolocation.requests', None)
    @patch('urllib.request.urlopen')
    def test_http_get_fallback_to_urllib(self, mock_urlopen):
        """Test fallback to urllib when requests not available."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"ip": "1.2.3.4"}'
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response
        
        result = _http_get('https://ipinfo.io/json', 5)
        
        assert result == '{"ip": "1.2.3.4"}'


class TestParseIpinfo:
    """Tests for _parse_ipinfo parser."""
    
    def test_parse_ipinfo_complete(self):
        """Test parsing complete ipinfo.io response."""
        text = json.dumps({
            "ip": "79.116.8.43",
            "city": "Madrid",
            "region": "Community of Madrid",
            "country": "ES",
            "org": "AS24940 Hetzner Online GmbH",
            "timezone": "Europe/Madrid"
        })
        
        result = _parse_ipinfo(text)
        
        assert result['public_ip'] == '79.116.8.43'
        assert result['city'] == 'Madrid'
        assert result['region'] == 'Community of Madrid'
        assert result['country'] == 'ES'
        assert 'Hetzner' in result['org']
        assert result['timezone'] == 'Europe/Madrid'
    
    def test_parse_ipinfo_missing_fields(self):
        """Test parsing ipinfo.io response with missing fields."""
        text = json.dumps({
            "ip": "1.2.3.4",
            "country": "US"
        })
        
        result = _parse_ipinfo(text)
        
        assert result['public_ip'] == '1.2.3.4'
        assert result['country'] == 'US'
        assert result['city'] == ''
        assert result['region'] == ''
        assert result['org'] == ''
        assert result['timezone'] == ''


class TestParseIpApi:
    """Tests for _parse_ip_api parser."""
    
    def test_parse_ip_api_complete(self):
        """Test parsing complete ip-api.com response."""
        text = json.dumps({
            "query": "1.2.3.4",
            "city": "London",
            "regionName": "England",
            "country": "United Kingdom",
            "isp": "British Telecom",
            "timezone": "Europe/London"
        })
        
        result = _parse_ip_api(text)
        
        assert result['public_ip'] == '1.2.3.4'
        assert result['city'] == 'London'
        assert result['region'] == 'England'
        assert result['country'] == 'United Kingdom'
        assert result['org'] == 'British Telecom'
        assert result['timezone'] == 'Europe/London'
    
    def test_parse_ip_api_alternative_fields(self):
        """Test parsing ip-api.com with alternative field names."""
        text = json.dumps({
            "ip": "5.6.7.8",  # Alternative to 'query'
            "city": "Paris",
            "region": "Île-de-France",  # Alternative to 'regionName'
            "country": "France",
            "org": "Orange SA",  # Alternative to 'isp'
            "timezone": "Europe/Paris"
        })
        
        result = _parse_ip_api(text)
        
        assert result['public_ip'] == '5.6.7.8'
        assert result['region'] == 'Île-de-France'
        assert result['org'] == 'Orange SA'
    
    def test_parse_ip_api_missing_fields(self):
        """Test parsing ip-api.com response with missing fields."""
        text = json.dumps({
            "query": "1.2.3.4"
        })
        
        result = _parse_ip_api(text)
        
        assert result['public_ip'] == '1.2.3.4'
        assert result['city'] == ''
        assert result['region'] == ''


class TestParseIpwhois:
    """Tests for _parse_ipwhois parser."""
    
    def test_parse_ipwhois_complete(self):
        """Test parsing complete ipwhois.app response."""
        text = json.dumps({
            "ip": "9.10.11.12",
            "city": "Tokyo",
            "region": "Tokyo",
            "country": "Japan",
            "org": "NTT Communications",
            "timezone": "Asia/Tokyo"
        })
        
        result = _parse_ipwhois(text)
        
        assert result['public_ip'] == '9.10.11.12'
        assert result['city'] == 'Tokyo'
        assert result['region'] == 'Tokyo'
        assert result['country'] == 'Japan'
        assert result['org'] == 'NTT Communications'
        assert result['timezone'] == 'Asia/Tokyo'
    
    def test_parse_ipwhois_asn_fallback(self):
        """Test parsing ipwhois.app with ASN name fallback."""
        text = json.dumps({
            "ip": "1.2.3.4",
            "country": "US",
            "asn": {
                "name": "Example ASN"
            }
        })
        
        result = _parse_ipwhois(text)
        
        assert result['public_ip'] == '1.2.3.4'
        assert result['org'] == 'Example ASN'
    
    def test_parse_ipwhois_missing_fields(self):
        """Test parsing ipwhois.app response with missing fields."""
        text = json.dumps({
            "ip": "1.2.3.4"
        })
        
        result = _parse_ipwhois(text)
        
        assert result['public_ip'] == '1.2.3.4'
        assert result['city'] == ''
        assert result['org'] == ''


class TestGetGeolocation:
    """Tests for get_geolocation function."""
    
    @patch('vpn_sentinel_common.geolocation._http_get')
    def test_get_geolocation_auto_ipinfo_success(self, mock_http_get):
        """Test auto mode uses ipinfo.io first."""
        mock_http_get.return_value = json.dumps({
            "ip": "79.116.8.43",
            "city": "Madrid",
            "country": "ES",
            "org": "Hetzner",
            "timezone": "Europe/Madrid"
        })
        
        result = get_geolocation(service='auto')
        
        assert result['public_ip'] == '79.116.8.43'
        assert result['city'] == 'Madrid'
        assert result['country'] == 'ES'
        assert result['source'] == 'ipinfo.io'
    
    @patch('vpn_sentinel_common.geolocation._http_get')
    def test_get_geolocation_fallback_to_ipapi(self, mock_http_get):
        """Test fallback to ip-api.com when ipinfo.io fails."""
        def mock_responses(url, timeout):
            if 'ipinfo.io' in url:
                return None  # First service fails
            elif 'ip-api.com' in url:
                return json.dumps({
                    "query": "1.2.3.4",
                    "city": "London",
                    "country": "GB"
                })
            return None
        
        mock_http_get.side_effect = mock_responses
        
        result = get_geolocation(service='auto')
        
        assert result['public_ip'] == '1.2.3.4'
        assert result['city'] == 'London'
        assert result['source'] == 'ip-api.com'
    
    @patch('vpn_sentinel_common.geolocation._http_get')
    def test_get_geolocation_fallback_to_ipwhois(self, mock_http_get):
        """Test fallback to ipwhois.app when first two fail."""
        def mock_responses(url, timeout):
            if 'ipwhois.app' in url:
                return json.dumps({
                    "ip": "5.6.7.8",
                    "city": "Berlin",
                    "country": "DE"
                })
            return None  # First two services fail
        
        mock_http_get.side_effect = mock_responses
        
        result = get_geolocation(service='auto')
        
        assert result['public_ip'] == '5.6.7.8'
        assert result['source'] == 'ipwhois.app'
    
    @patch('vpn_sentinel_common.geolocation._http_get')
    def test_get_geolocation_specific_service(self, mock_http_get):
        """Test requesting specific service."""
        mock_http_get.return_value = json.dumps({
            "query": "1.2.3.4",
            "city": "Paris",
            "country": "FR"
        })
        
        result = get_geolocation(service='ip-api.com')
        
        assert result['public_ip'] == '1.2.3.4'
        assert result['source'] == 'ip-api.com'
        # Should only call ip-api, not others
        mock_http_get.assert_called_once()
    
    @patch('vpn_sentinel_common.geolocation._http_get')
    def test_get_geolocation_all_services_fail(self, mock_http_get):
        """Test returns empty dict when all services fail."""
        mock_http_get.return_value = None
        
        result = get_geolocation(service='auto')
        
        assert result == {}
    
    @patch('vpn_sentinel_common.geolocation._http_get')
    def test_get_geolocation_invalid_service(self, mock_http_get):
        """Test returns empty dict for invalid service name."""
        result = get_geolocation(service='invalid-service')
        
        assert result == {}
        mock_http_get.assert_not_called()
    
    @patch('vpn_sentinel_common.geolocation._http_get')
    def test_get_geolocation_parse_exception(self, mock_http_get):
        """Test handles JSON parse errors gracefully."""
        mock_http_get.return_value = "invalid json {["
        
        result = get_geolocation(service='ipinfo.io')
        
        assert result == {}
    
    @patch('vpn_sentinel_common.geolocation._http_get')
    def test_get_geolocation_no_public_ip(self, mock_http_get):
        """Test skips response without public_ip field."""
        def mock_responses(url, timeout):
            if 'ipinfo.io' in url:
                return json.dumps({"city": "London"})  # No IP!
            elif 'ip-api.com' in url:
                return json.dumps({"query": "1.2.3.4", "city": "Paris"})
            return None
        
        mock_http_get.side_effect = mock_responses
        
        result = get_geolocation(service='auto')
        
        # Should skip ipinfo and use ip-api
        assert result['public_ip'] == '1.2.3.4'
        assert result['source'] == 'ip-api.com'
    
    @patch('vpn_sentinel_common.geolocation._http_get')
    def test_get_geolocation_custom_timeout(self, mock_http_get):
        """Test custom timeout is passed to HTTP GET."""
        mock_http_get.return_value = json.dumps({
            "ip": "1.2.3.4",
            "country": "US"
        })
        
        result = get_geolocation(service='ipinfo.io', timeout=10)
        
        assert result['public_ip'] == '1.2.3.4'
        mock_http_get.assert_called_once()
        assert mock_http_get.call_args[0][1] == 10  # Check timeout arg
