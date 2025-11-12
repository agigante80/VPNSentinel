"""
Unit tests for Payload module (payload.py)
Tests payload building and posting functions.
"""
import pytest
from unittest.mock import patch, MagicMock, mock_open
import json
import sys
import os
import tempfile

# Add common library to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from vpn_sentinel_common.payload import build_payload_from_env, post_payload


class TestBuildPayloadFromEnv:
    """Tests for build_payload_from_env function."""
    
    @patch.dict(os.environ, {
        'CLIENT_ID': 'test-client',
        'PUBLIC_IP': '1.2.3.4',
        'COUNTRY': 'GB',
        'CITY': 'London',
        'REGION': 'England',
        'ORG': 'Test ISP',
        'VPN_TIMEZONE': 'Europe/London',
        'DNS_LOC': 'GB',
        'DNS_COLO': 'LHR'
    })
    def test_build_payload_complete(self):
        """Test building payload with all environment variables."""
        payload = build_payload_from_env()
        
        assert payload['client_id'] == 'test-client'
        assert payload['public_ip'] == '1.2.3.4'
        assert payload['status'] == 'alive'
        assert payload['location']['country'] == 'GB'
        assert payload['location']['city'] == 'London'
        assert payload['location']['region'] == 'England'
        assert payload['location']['org'] == 'Test ISP'
        assert payload['location']['timezone'] == 'Europe/London'
        assert payload['dns_test']['location'] == 'GB'
        assert payload['dns_test']['colo'] == 'LHR'
        assert 'timestamp' in payload
    
    @patch.dict(os.environ, {
        'VPN_SENTINEL_CLIENT_ID': 'sentinel-client'
    }, clear=True)
    def test_build_payload_alternative_client_id(self):
        """Test CLIENT_ID fallback to VPN_SENTINEL_CLIENT_ID."""
        payload = build_payload_from_env()
        
        assert payload['client_id'] == 'sentinel-client'
    
    @patch.dict(os.environ, {}, clear=True)
    def test_build_payload_defaults(self):
        """Test payload uses defaults when environment variables missing."""
        payload = build_payload_from_env()
        
        assert payload['client_id'] == ''
        assert payload['public_ip'] == 'unknown'
        assert payload['location']['country'] == 'Unknown'
        assert payload['location']['city'] == 'Unknown'
        assert payload['location']['region'] == 'Unknown'
        assert payload['location']['org'] == 'Unknown'
        assert payload['dns_test']['location'] == 'Unknown'
        assert payload['dns_test']['colo'] == 'Unknown'
    
    def test_build_payload_timestamp_format(self):
        """Test timestamp has correct ISO format."""
        payload = build_payload_from_env()
        
        assert 'timestamp' in payload
        # Should be ISO format with timezone
        assert 'T' in payload['timestamp']
        assert len(payload['timestamp']) > 10


class TestPostPayload:
    """Tests for post_payload function."""
    
    def test_post_payload_to_capture_file(self):
        """Test payload is written to capture file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            capture_path = f.name
        
        try:
            test_payload = json.dumps({
                'client_id': 'test',
                'public_ip': '1.2.3.4'
            })
            
            with patch.dict(os.environ, {'VPN_SENTINEL_TEST_CAPTURE_PATH': capture_path}):
                result = post_payload(test_payload)
            
            assert result == 0
            
            # Verify file contents
            with open(capture_path, 'r') as f:
                contents = f.read()
                assert 'test' in contents
                assert '1.2.3.4' in contents
        finally:
            if os.path.exists(capture_path):
                os.unlink(capture_path)
    
    def test_post_payload_creates_capture_directory(self):
        """Test capture file directory is created if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            capture_path = os.path.join(tmpdir, 'subdir', 'capture.json')
            test_payload = json.dumps({'client_id': 'test'})
            
            with patch.dict(os.environ, {'VPN_SENTINEL_TEST_CAPTURE_PATH': capture_path}):
                result = post_payload(test_payload)
            
            assert result == 0
            assert os.path.exists(capture_path)
    
    def test_post_payload_invalid_json_fallback(self):
        """Test non-JSON payload is still written as plain text."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            capture_path = f.name
        
        try:
            invalid_payload = "not valid json {"
            
            with patch.dict(os.environ, {'VPN_SENTINEL_TEST_CAPTURE_PATH': capture_path}):
                result = post_payload(invalid_payload)
            
            assert result == 0
            
            # Verify file was written (as plain text)
            with open(capture_path, 'r') as f:
                contents = f.read()
                assert 'not valid json' in contents
        finally:
            if os.path.exists(capture_path):
                os.unlink(capture_path)
    
    @patch('urllib.request.urlopen')
    @patch.dict(os.environ, {
        'SERVER_URL': 'http://localhost:5000/api/v1/keepalive',
        'VPN_SENTINEL_API_KEY': 'test-key'
    })
    def test_post_payload_http_success(self, mock_urlopen):
        """Test successful HTTP POST to server."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response
        
        test_payload = json.dumps({'client_id': 'test'})
        result = post_payload(test_payload)
        
        assert result == 0
        mock_urlopen.assert_called_once()
    
    @patch('urllib.request.urlopen')
    @patch.dict(os.environ, {
        'VPN_SENTINEL_URL': 'http://localhost:5000',
        'VPN_SENTINEL_API_PATH': '/api/v1'
    })
    def test_post_payload_builds_url_from_components(self, mock_urlopen):
        """Test URL is built from VPN_SENTINEL_URL and API_PATH."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response
        
        test_payload = json.dumps({'client_id': 'test'})
        result = post_payload(test_payload)
        
        assert result == 0
        # Check URL was constructed correctly
        call_args = mock_urlopen.call_args[0][0]
        assert 'localhost:5000' in call_args.full_url
        assert '/api/v1/keepalive' in call_args.full_url
    
    @patch('urllib.request.urlopen')
    @patch.dict(os.environ, {
        'SERVER_URL': 'http://localhost:5000/keepalive',
        'VPN_SENTINEL_API_KEY': 'secret-key'
    })
    def test_post_payload_includes_auth_header(self, mock_urlopen):
        """Test X-API-Key header is included when API key set."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response
        
        test_payload = json.dumps({'client_id': 'test'})
        result = post_payload(test_payload)
        
        assert result == 0
        request = mock_urlopen.call_args[0][0]
        assert 'X-api-key' in request.headers
        assert request.headers['X-api-key'] == 'secret-key'
    
    @patch('urllib.request.urlopen')
    @patch.dict(os.environ, {
        'SERVER_URL': 'http://localhost:5000/keepalive',
        'TIMEOUT': '60'
    })
    def test_post_payload_custom_timeout(self, mock_urlopen):
        """Test custom timeout is used."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response
        
        test_payload = json.dumps({'client_id': 'test'})
        result = post_payload(test_payload)
        
        assert result == 0
        assert mock_urlopen.call_args[1]['timeout'] == 60.0
    
    @patch('urllib.request.urlopen')
    @patch.dict(os.environ, {
        'SERVER_URL': 'https://localhost:5000/keepalive',
        'VPN_SENTINEL_ALLOW_INSECURE': 'true'
    })
    def test_post_payload_insecure_tls(self, mock_urlopen):
        """Test insecure TLS context when flag is set."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response
        
        test_payload = json.dumps({'client_id': 'test'})
        result = post_payload(test_payload)
        
        assert result == 0
        # Context should be passed
        assert mock_urlopen.call_args[1]['context'] is not None
    
    @patch('urllib.request.urlopen')
    @patch.dict(os.environ, {
        'SERVER_URL': 'http://localhost:5000/keepalive'
    })
    def test_post_payload_http_error(self, mock_urlopen):
        """Test HTTP error returns non-zero."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 500
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response
        
        test_payload = json.dumps({'client_id': 'test'})
        result = post_payload(test_payload)
        
        assert result == 1
    
    @patch('urllib.request.urlopen')
    @patch.dict(os.environ, {
        'SERVER_URL': 'http://localhost:5000/keepalive'
    })
    def test_post_payload_network_exception(self, mock_urlopen):
        """Test network exception returns non-zero."""
        mock_urlopen.side_effect = Exception("Network error")
        
        test_payload = json.dumps({'client_id': 'test'})
        result = post_payload(test_payload)
        
        assert result == 1
    
    @patch('urllib.request.urlopen')
    @patch.dict(os.environ, {
        'SERVER_URL': 'http://localhost:5000/api/v1/keepalive/'
    })
    def test_post_payload_strips_trailing_slashes(self, mock_urlopen):
        """Test trailing slashes are handled when using SERVER_URL."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response
        
        test_payload = json.dumps({'client_id': 'test'})
        result = post_payload(test_payload)
        
        assert result == 0
        request = mock_urlopen.call_args[0][0]
        # URL should contain keepalive endpoint
        assert '/keepalive' in request.full_url
    
    @patch('urllib.request.urlopen')
    @patch.dict(os.environ, {
        'VPN_SENTINEL_URL': 'http://localhost:5000/',
        'VPN_SENTINEL_API_PATH': '/api/v1/'
    })
    def test_post_payload_strips_slashes_from_components(self, mock_urlopen):
        """Test slashes are stripped when building URL from components."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response
        
        test_payload = json.dumps({'client_id': 'test'})
        result = post_payload(test_payload)
        
        assert result == 0
        request = mock_urlopen.call_args[0][0]
        # Should not have double slashes
        assert '//' not in request.full_url.replace('http://', '')
    
    def test_post_payload_capture_write_failure(self):
        """Test capture file write failure returns non-zero."""
        # Use invalid path that can't be created
        invalid_path = '/root/impossible/path/capture.json'
        test_payload = json.dumps({'client_id': 'test'})
        
        with patch.dict(os.environ, {'VPN_SENTINEL_TEST_CAPTURE_PATH': invalid_path}):
            with patch('os.makedirs', side_effect=Exception("Permission denied")):
                with patch('builtins.open', side_effect=Exception("Cannot write")):
                    result = post_payload(test_payload)
        
        assert result == 1
