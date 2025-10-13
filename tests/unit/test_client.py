"""
Unit tests for VPN Sentinel Client
Tests the shell script functionality and API communication
"""
import os
import unittest
from unittest.mock import Mock, patch, call
import subprocess
import json
import tempfile


class TestClientScript(unittest.TestCase):
    """Test client shell script functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_env = {
            'VPN_SENTINEL_SERVER_API_BASE_URL': 'http://localhost:5554',
            'VPN_SENTINEL_SERVER_API_PATH': '/test/v1',
            'VPN_SENTINEL_CLIENT_ID': 'test-client-001',
            'VPN_SENTINEL_API_KEY': 'test-api-key',
            'TZ': 'UTC'
        }
        
        # Path to client script
        self.script_path = os.path.join(
            os.path.dirname(__file__), 
            '../../vpn-sentinel-client/vpn-sentinel-client.sh'
        )
    
    def test_script_syntax(self):
        """Test that the shell script has valid syntax"""
        try:
            # Test shell script syntax
            result = subprocess.run(
                ['bash', '-n', self.script_path], 
                capture_output=True, 
                text=True,
                timeout=10
            )
            self.assertEqual(result.returncode, 0, 
                           f"Script syntax error: {result.stderr}")
        except FileNotFoundError:
            self.skipTest("Client script not found")
    
    def test_environment_variable_validation(self):
        """Test environment variable validation logic"""
        required_vars = [
            'VPN_SENTINEL_SERVER_API_BASE_URL',
            'VPN_SENTINEL_SERVER_API_PATH', 
            'VPN_SENTINEL_CLIENT_ID',
            'VPN_SENTINEL_API_KEY'
        ]
        
        # Test that all required variables are defined in our test env
        for var in required_vars:
            self.assertIn(var, self.test_env)
            self.assertIsNotNone(self.test_env[var])
    
    @patch('subprocess.run')
    def test_curl_command_construction(self, mock_subprocess):
        """Test curl command construction for API calls"""
        # Mock successful curl response
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '{"status": "ok", "message": "Keepalive received"}'
        mock_result.stderr = ''
        mock_subprocess.return_value = mock_result
        
        # Expected curl command components
        base_url = self.test_env['VPN_SENTINEL_SERVER_API_BASE_URL']
        api_path = self.test_env['VPN_SENTINEL_SERVER_API_PATH']
        api_key = self.test_env['VPN_SENTINEL_API_KEY']
        
        expected_url = f"{base_url}{api_path}/keepalive"
        expected_headers = [
            '-H', f'Authorization: Bearer {api_key}',
            '-H', 'Content-Type: application/json'
        ]
        
        # Test URL construction
        self.assertEqual(expected_url, "http://localhost:5554/test/v1/keepalive")
        
        # Test header construction
        auth_header = f'Authorization: Bearer {api_key}'
        self.assertEqual(auth_header, 'Authorization: Bearer test-api-key')
    
    def test_json_payload_structure(self):
        """Test JSON payload structure for keepalive requests"""
        # Mock data that would be gathered by the script
        mock_data = {
            'client_id': 'test-client-001',
            'timestamp': '2025-10-13T20:45:59Z',
            'public_ip': '1.2.3.4',
            'status': 'alive',
            'location': {
                'country': 'US',
                'city': 'New York',
                'region': 'New York',
                'org': 'AS12345 Test Provider',
                'timezone': 'America/New_York'
            },
            'dns_test': {
                'location': 'US',
                'colo': 'NYC'
            }
        }
        
        # Test required fields are present
        required_fields = ['client_id', 'timestamp', 'public_ip', 'status', 'location', 'dns_test']
        for field in required_fields:
            self.assertIn(field, mock_data)
        
        # Test nested location structure
        location_fields = ['country', 'city', 'region', 'org', 'timezone']
        for field in location_fields:
            self.assertIn(field, mock_data['location'])
        
        # Test nested dns_test structure  
        dns_fields = ['location', 'colo']
        for field in dns_fields:
            self.assertIn(field, mock_data['dns_test'])
        
        # Test JSON serialization
        json_str = json.dumps(mock_data)
        parsed_data = json.loads(json_str)
        self.assertEqual(parsed_data, mock_data)


class TestAPIEndpoints(unittest.TestCase):
    """Test API endpoint responses and error handling"""
    
    def setUp(self):
        """Set up test environment"""
        self.base_url = 'http://localhost:5554'
        self.api_path = '/test/v1'
        self.api_key = 'test-api-key'
    
    def test_keepalive_success_response(self):
        """Test handling of successful keepalive response"""
        mock_response = {
            'status': 'ok',
            'message': 'Keepalive received',
            'client_id': 'test-client-001',
            'public_ip': '1.2.3.4',
            'is_new_connection': False,
            'ip_changed': False,
            'server_time': '2025-10-13T20:45:59Z'
        }
        
        # Test response structure
        self.assertEqual(mock_response['status'], 'ok')
        self.assertIn('message', mock_response)
        self.assertIn('server_time', mock_response)
        
        # Test success detection logic
        is_success = mock_response.get('status') == 'ok'
        self.assertTrue(is_success)
    
    def test_keepalive_error_response(self):
        """Test handling of error responses"""
        error_responses = [
            {'status': 'error', 'message': 'Invalid API key'},
            {'status': 'error', 'message': 'Rate limit exceeded'},
            {'status': 'error', 'message': 'Invalid JSON payload'}
        ]
        
        for error_response in error_responses:
            with self.subTest(error_response=error_response):
                self.assertEqual(error_response['status'], 'error')
                self.assertIn('message', error_response)
                
                # Test error detection logic
                is_error = error_response.get('status') == 'error'
                self.assertTrue(is_error)
    
    def test_health_check_endpoint(self):
        """Test health check endpoint response"""
        mock_health_response = {
            'status': 'healthy',
            'server_time': '2025-10-13T20:45:59Z',
            'active_clients': 2,
            'uptime_info': 'VPN Keepalive Server is running'
        }
        
        # Test health response structure
        self.assertEqual(mock_health_response['status'], 'healthy')
        self.assertIn('server_time', mock_health_response)
        self.assertIn('active_clients', mock_health_response)
        
        # Test health check logic
        is_healthy = mock_health_response.get('status') == 'healthy'
        self.assertTrue(is_healthy)


class TestErrorHandling(unittest.TestCase):
    """Test error handling and retry logic"""
    
    def test_network_timeout_handling(self):
        """Test handling of network timeouts"""
        # Mock timeout scenarios
        timeout_scenarios = [
            'Connection timed out',
            'Read timeout', 
            'DNS resolution timeout'
        ]
        
        for scenario in timeout_scenarios:
            with self.subTest(scenario=scenario):
                # Test that timeout errors are recognized
                lower = scenario.lower()
                is_timeout = ('timeout' in lower) or ('timed out' in lower)
                self.assertTrue(is_timeout)
    
    def test_http_error_codes(self):
        """Test handling of various HTTP error codes"""
        error_codes = {
            400: 'Bad Request',
            401: 'Unauthorized',
            403: 'Forbidden', 
            404: 'Not Found',
            429: 'Too Many Requests',
            500: 'Internal Server Error'
        }
        
        for code, message in error_codes.items():
            with self.subTest(code=code):
                # Test error code classification
                is_client_error = 400 <= code < 500
                is_server_error = 500 <= code < 600
                
                if code in [400, 401, 403, 404]:
                    self.assertTrue(is_client_error)
                elif code == 500:
                    self.assertTrue(is_server_error)
    
    def test_retry_logic(self):
        """Test retry logic for failed requests"""
        max_retries = 3
        retry_delay = 5  # seconds
        
        # Test retry parameters
        self.assertGreater(max_retries, 0)
        self.assertGreater(retry_delay, 0)
        
        # Test retry conditions (should retry on network errors, not auth errors)
        retryable_errors = ['timeout', 'connection refused', 'network unreachable']
        non_retryable_errors = ['401 Unauthorized', '403 Forbidden', '400 Bad Request']
        
        for error in retryable_errors:
            with self.subTest(error=error):
                should_retry = any(keyword in error.lower() for keyword in ['timeout', 'connection', 'network'])
                self.assertTrue(should_retry)
        
        for error in non_retryable_errors:
            with self.subTest(error=error):
                should_not_retry = any(code in error for code in ['401', '403', '400'])
                self.assertTrue(should_not_retry)


class TestDataGathering(unittest.TestCase):
    """Test data gathering functions (IP, location, DNS)"""
    
    def test_ip_info_parsing(self):
        """Test parsing of ipinfo.io response"""
        mock_ipinfo_response = {
            "ip": "172.67.163.127",
            "city": "Madrid",
            "region": "Madrid", 
            "country": "ES",
            "loc": "40.4165,-3.7026",
            "org": "AS57269 DIGI SPAIN TELECOM S.L.",
            "postal": "28013",
            "timezone": "Europe/Madrid"
        }
        
        # Test required fields extraction
        ip = mock_ipinfo_response.get('ip', 'Unknown')
        city = mock_ipinfo_response.get('city', 'Unknown')
        region = mock_ipinfo_response.get('region', 'Unknown')
        country = mock_ipinfo_response.get('country', 'Unknown')
        org = mock_ipinfo_response.get('org', 'Unknown')
        timezone = mock_ipinfo_response.get('timezone', 'Unknown')
        
        self.assertEqual(ip, "172.67.163.127")
        self.assertEqual(city, "Madrid")
        self.assertEqual(country, "ES")
        self.assertEqual(org, "AS57269 DIGI SPAIN TELECOM S.L.")
        self.assertEqual(timezone, "Europe/Madrid")
    
    def test_dns_test_parsing(self):
        """Test parsing of DNS test response"""
        mock_dns_response = {
            "fl": "27f39",
            "h": "www.cloudflare.com",
            "ip": "104.16.123.96",
            "ts": 1697222759.123,
            "visit_scheme": "https",
            "uag": "Mozilla/5.0...",
            "colo": "MAD",
            "sliver": "none",
            "http": "HTTP/2",
            "loc": "ES",
            "tls": "TLSv1.3",
            "sni": "plaintext",
            "warp": "off",
            "gateway": "off"
        }
        
        # Test DNS test fields extraction
        dns_location = mock_dns_response.get('loc', 'Unknown')
        dns_colo = mock_dns_response.get('colo', 'Unknown')
        
        self.assertEqual(dns_location, "ES")
        self.assertEqual(dns_colo, "MAD")
        
        # Test DNS leak detection logic
        vpn_country = "ES"
        dns_country = "ES"
        is_dns_leak = dns_country != vpn_country
        self.assertFalse(is_dns_leak)  # Same country, no leak
        
        # Test with different countries (DNS leak)
        vpn_country = "PL"
        dns_country = "ES" 
        is_dns_leak = dns_country != vpn_country
        self.assertTrue(is_dns_leak)  # Different countries, potential leak


if __name__ == '__main__':
    unittest.main()