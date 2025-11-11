"""
Unit tests for Server Info (server_info.py)
Tests server IP detection, geolocation, DNS status checks.
"""
import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add common library to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from vpn_sentinel_common.server_info import get_server_public_ip, get_server_info


class TestGetServerPublicIp:
    """Tests for get_server_public_ip function."""
    
    @patch('vpn_sentinel_common.server_info.requests.get')
    def test_success_with_ipinfo(self, mock_get):
        """Test successful IP retrieval from ipinfo.io."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'ip': '79.116.8.43'}
        mock_get.return_value = mock_response
        
        result = get_server_public_ip()
        
        assert result == '79.116.8.43'
        mock_get.assert_called_once_with('https://ipinfo.io/json', timeout=10, verify=True)
    
    @patch('vpn_sentinel_common.server_info.requests.get')
    def test_fallback_to_ipify(self, mock_get):
        """Test fallback to ipify when ipinfo fails."""
        def mock_responses(url, **kwargs):
            if 'ipinfo.io' in url:
                raise Exception("ipinfo.io failed")
            elif 'ipify.org' in url:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {'ip': '1.2.3.4'}
                return mock_resp
        
        mock_get.side_effect = mock_responses
        
        result = get_server_public_ip()
        
        assert result == '1.2.3.4'
        assert mock_get.call_count == 2
    
    @patch('vpn_sentinel_common.server_info.requests.get')
    def test_returns_unknown_on_failure(self, mock_get):
        """Test returns 'Unknown' when both services fail."""
        mock_get.side_effect = Exception("Network error")
        
        result = get_server_public_ip()
        
        assert result == 'Unknown'
    
    @patch('vpn_sentinel_common.server_info.requests.get')
    def test_handles_non_200_status(self, mock_get):
        """Test handles non-200 status codes gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        result = get_server_public_ip()
        
        assert result == 'Unknown'
    
    @patch('vpn_sentinel_common.server_info.requests.get')
    def test_handles_missing_ip_field(self, mock_get):
        """Test handles response without 'ip' field."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'error': 'No IP found'}
        mock_get.return_value = mock_response
        
        result = get_server_public_ip()
        
        assert result == 'Unknown'


class TestGetServerInfo:
    """Tests for get_server_info function."""
    
    @patch('socket.gethostbyname')
    @patch('vpn_sentinel_common.server_info.requests.get')
    @patch('vpn_sentinel_common.server_info.log_info')
    def test_success_with_ipinfo(self, mock_log, mock_get, mock_socket):
        """Test successful info retrieval from ipinfo.io."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'ip': '79.116.8.43',
            'city': 'Madrid',
            'region': 'Community of Madrid',
            'country': 'ES',
            'org': 'AS24940 Hetzner Online GmbH'
        }
        mock_get.return_value = mock_response
        mock_socket.return_value = '8.8.8.8'  # DNS working
        
        result = get_server_info()
        
        assert result['public_ip'] == '79.116.8.43'
        assert result['location'] == 'Madrid, Community of Madrid, ES'
        assert 'Hetzner' in result['provider']
        assert result['dns_status'] == 'Operational'
    
    @patch('socket.gethostbyname')
    @patch('vpn_sentinel_common.server_info.requests.get')
    @patch('vpn_sentinel_common.server_info.log_info')
    @patch('vpn_sentinel_common.server_info.log_warn')
    def test_fallback_to_ipapi(self, mock_warn, mock_log, mock_get, mock_socket):
        """Test fallback to ip-api.com when ipinfo fails."""
        def mock_responses(url, **kwargs):
            if 'ipinfo.io' in url:
                mock_resp = MagicMock()
                mock_resp.status_code = 500
                return mock_resp
            elif 'ip-api.com' in url:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {
                    'query': '1.2.3.4',
                    'city': 'London',
                    'regionName': 'England',
                    'countryCode': 'GB',
                    'isp': 'British Telecom'
                }
                return mock_resp
        
        mock_get.side_effect = mock_responses
        mock_socket.return_value = '8.8.8.8'
        
        result = get_server_info()
        
        assert result['public_ip'] == '1.2.3.4'
        assert result['location'] == 'London, England, GB'
        assert result['provider'] == 'British Telecom'
        mock_warn.assert_called_once()
    
    @patch('socket.gethostbyname')
    @patch('vpn_sentinel_common.server_info.requests.get')
    @patch('vpn_sentinel_common.server_info.log_info')
    def test_location_without_region(self, mock_log, mock_get, mock_socket):
        """Test location formatting when region is missing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'ip': '1.2.3.4',
            'city': 'Singapore',
            'region': '',  # No region
            'country': 'SG',
            'org': 'Example ISP'
        }
        mock_get.return_value = mock_response
        mock_socket.return_value = '8.8.8.8'
        
        result = get_server_info()
        
        assert result['location'] == 'Singapore, SG'
    
    @patch('socket.gethostbyname')
    @patch('vpn_sentinel_common.server_info.requests.get')
    @patch('vpn_sentinel_common.server_info.log_info')
    def test_location_without_city(self, mock_log, mock_get, mock_socket):
        """Test location formatting when city is missing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'ip': '1.2.3.4',
            'city': '',  # No city
            'region': '',
            'country': 'US',
            'org': 'Example ISP'
        }
        mock_get.return_value = mock_response
        mock_socket.return_value = '8.8.8.8'
        
        result = get_server_info()
        
        assert result['location'] == 'US'
    
    @patch('socket.gethostbyname')
    @patch('vpn_sentinel_common.server_info.requests.get')
    @patch('vpn_sentinel_common.server_info.log_info')
    def test_dns_failure_detection(self, mock_log, mock_get, mock_socket):
        """Test DNS status detection when DNS fails."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'ip': '1.2.3.4',
            'city': 'Test',
            'country': 'US',
            'org': 'Test ISP'
        }
        mock_get.return_value = mock_response
        mock_socket.side_effect = Exception("DNS resolution failed")
        
        result = get_server_info()
        
        assert result['dns_status'] == 'Issues Detected'
    
    @patch('vpn_sentinel_common.server_info.requests.get')
    @patch('vpn_sentinel_common.server_info.log_error')
    def test_complete_failure_returns_defaults(self, mock_log_error, mock_get):
        """Test returns default values when everything fails."""
        mock_get.side_effect = Exception("Network down")
        
        result = get_server_info()
        
        assert result['public_ip'] == 'Unknown'
        assert result['location'] == 'Unknown'
        assert result['provider'] == 'Unknown'
        assert result['dns_status'] == 'Unknown'
        mock_log_error.assert_called_once()
    
    @patch('socket.gethostbyname')
    @patch('vpn_sentinel_common.server_info.requests.get')
    @patch('vpn_sentinel_common.server_info.log_info')
    def test_ipapi_location_without_region(self, mock_log, mock_get, mock_socket):
        """Test ip-api.com location formatting without region."""
        def mock_responses(url, **kwargs):
            if 'ipinfo.io' in url:
                mock_resp = MagicMock()
                mock_resp.status_code = 500
                return mock_resp
            elif 'ip-api.com' in url:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {
                    'query': '1.2.3.4',
                    'city': 'Tokyo',
                    'regionName': '',  # No region
                    'countryCode': 'JP',
                    'isp': 'NTT'
                }
                return mock_resp
        
        mock_get.side_effect = mock_responses
        mock_socket.return_value = '8.8.8.8'
        
        result = get_server_info()
        
        assert result['location'] == 'Tokyo, JP'
    
    @patch('socket.gethostbyname')
    @patch('vpn_sentinel_common.server_info.requests.get')
    @patch('vpn_sentinel_common.server_info.log_info')
    @patch('vpn_sentinel_common.server_info.log_warn')
    def test_both_services_fail(self, mock_warn, mock_log, mock_get, mock_socket):
        """Test when both geolocation services fail."""
        def mock_responses(url, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 500
            return mock_resp
        
        mock_get.side_effect = mock_responses
        mock_socket.return_value = '8.8.8.8'
        
        result = get_server_info()
        
        # Should still return dict with Unknown values
        assert result['public_ip'] == 'Unknown'
        assert result['location'] == 'Unknown'
    
    @patch('socket.gethostbyname')
    @patch('vpn_sentinel_common.server_info.requests.get')
    @patch('vpn_sentinel_common.server_info.log_info')
    def test_handles_missing_provider_field(self, mock_log, mock_get, mock_socket):
        """Test handles missing provider/org field gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'ip': '1.2.3.4',
            'city': 'Test',
            'country': 'US'
            # Missing 'org' field
        }
        mock_get.return_value = mock_response
        mock_socket.return_value = '8.8.8.8'
        
        result = get_server_info()
        
        assert result['provider'] == 'Unknown Provider'
