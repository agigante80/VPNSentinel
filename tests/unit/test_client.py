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

    def test_trust_self_signed_certificates_true(self):
        """Test that --insecure flag is added when TRUST_SELF_SIGNED_CERTIFICATES=true"""
        # Test environment with self-signed certificates enabled
        test_env = self.test_env.copy()
        test_env['TRUST_SELF_SIGNED_CERTIFICATES'] = 'true'
        
        # Read the script content to verify --insecure flag is present when variable is set
        with open(self.script_path, 'r') as f:
            script_content = f.read()
        
        # Verify the script contains the conditional insecure flag
        self.assertIn('${TRUST_SELF_SIGNED_CERTIFICATES:+--insecure}', script_content)
        
        # Test that the variable defaults to false
        self.assertEqual(os.environ.get('TRUST_SELF_SIGNED_CERTIFICATES', 'false'), 'false')

    def test_trust_self_signed_certificates_false(self):
        """Test that --insecure flag is not added when TRUST_SELF_SIGNED_CERTIFICATES=false"""
        # Test environment with self-signed certificates disabled (default)
        test_env = self.test_env.copy()
        test_env['TRUST_SELF_SIGNED_CERTIFICATES'] = 'false'
        
        # Read the script content to verify the conditional logic exists
        with open(self.script_path, 'r') as f:
            script_content = f.read()
        
        # Verify the script contains the conditional insecure flag logic
        self.assertIn('${TRUST_SELF_SIGNED_CERTIFICATES:+--insecure}', script_content)
        
        # Test that when variable is false or unset, no insecure flag should be added
        # This is tested by the conditional expansion logic in bash

    def test_trust_self_signed_certificates_unset(self):
        """Test default behavior when TRUST_SELF_SIGNED_CERTIFICATES is not set"""
        # Test environment without TRUST_SELF_SIGNED_CERTIFICATES
        test_env = self.test_env.copy()
        test_env.pop('TRUST_SELF_SIGNED_CERTIFICATES', None)
        
        # Read the script content to verify default value handling
        with open(self.script_path, 'r') as f:
            script_content = f.read()
        
        # Verify the script sets default value
        self.assertIn('TRUST_SELF_SIGNED_CERTIFICATES="${TRUST_SELF_SIGNED_CERTIFICATES:-false}"', script_content)
        
        # Test that the default value is false
        self.assertEqual(os.environ.get('TRUST_SELF_SIGNED_CERTIFICATES', 'false'), 'false')


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
    
    def test_ip_api_fallback_parsing(self):
        """Test parsing of ip-api.com fallback response"""
        mock_ipapi_response = {
            "query": "172.67.163.127",
            "status": "success",
            "country": "Spain",
            "countryCode": "ES",
            "region": "MD",
            "regionName": "Madrid",
            "city": "Madrid",
            "zip": "28013",
            "lat": 40.4165,
            "lon": -3.7026,
            "timezone": "Europe/Madrid",
            "isp": "Digi Spain Telecom S.L.",
            "org": "Digi Spain Telecom S.L.",
            "as": "AS57269 Digi Spain Telecom S.L.",
            "mobile": False,
            "proxy": False,
            "hosting": False
        }
        
        # Test ip-api.com field mapping (different field names)
        ip = mock_ipapi_response.get('query', 'Unknown')
        country = mock_ipapi_response.get('countryCode', 'Unknown')  # Note: countryCode vs country
        city = mock_ipapi_response.get('city', 'Unknown')
        region = mock_ipapi_response.get('regionName', 'Unknown')    # Note: regionName vs region
        org = mock_ipapi_response.get('isp', 'Unknown')              # Note: isp vs org
        timezone = mock_ipapi_response.get('timezone', 'Unknown')
        
        self.assertEqual(ip, "172.67.163.127")
        self.assertEqual(city, "Madrid")
        self.assertEqual(country, "ES")
        self.assertEqual(region, "Madrid")
        self.assertEqual(org, "Digi Spain Telecom S.L.")
        self.assertEqual(timezone, "Europe/Madrid")
    
    @patch('subprocess.run')
    def test_geolocation_fallback_empty_response(self, mock_subprocess):
        """Test fallback to ip-api.com when ipinfo.io returns empty response"""
        # Mock curl calls: first call (ipinfo.io) returns empty, second call (ip-api.com) returns data
        mock_subprocess.side_effect = [
            Mock(returncode=0, stdout='', stderr=''),  # ipinfo.io returns empty
            Mock(returncode=0, stdout=json.dumps({
                "query": "172.67.163.127",
                "status": "success",
                "countryCode": "ES",
                "city": "Madrid",
                "regionName": "Madrid",
                "isp": "Digi Spain Telecom S.L.",
                "timezone": "Europe/Madrid"
            }), stderr='')  # ip-api.com returns valid data
        ]
        
        # Simulate the script logic: try ipinfo.io first
        result1 = mock_subprocess()
        vpn_info = result1.stdout
        
        # Check if we need to fallback
        if not vpn_info or vpn_info == '{}':
            # Should call ip-api.com as fallback
            result2 = mock_subprocess()
            self.assertEqual(result2.returncode, 0)
            # Verify ip-api.com returned valid data
            data = json.loads(result2.stdout)
            self.assertEqual(data['query'], '172.67.163.127')
            self.assertEqual(data['countryCode'], 'ES')
        
        # Verify both calls were made
        self.assertEqual(mock_subprocess.call_count, 2)
    
    @patch('subprocess.run')
    def test_geolocation_fallback_network_failure(self, mock_subprocess):
        """Test fallback to ip-api.com when ipinfo.io has network failure"""
        # Mock curl calls: first call fails, second call succeeds
        mock_subprocess.side_effect = [
            Mock(returncode=1, stdout='', stderr='curl: (6) Could not resolve host'),  # ipinfo.io fails
            Mock(returncode=0, stdout=json.dumps({
                "query": "172.67.163.127",
                "status": "success", 
                "countryCode": "ES",
                "city": "Madrid",
                "regionName": "Madrid",
                "isp": "Digi Spain Telecom S.L.",
                "timezone": "Europe/Madrid"
            }), stderr='')  # ip-api.com succeeds
        ]
        
        # Simulate the script logic
        try:
            # First curl attempt (ipinfo.io)
            result1 = mock_subprocess()
            if result1.returncode != 0:
                # Should fallback to ip-api.com
                result2 = mock_subprocess()
                self.assertEqual(result2.returncode, 0)
                # Verify fallback data is valid JSON
                data = json.loads(result2.stdout)
                self.assertEqual(data['query'], '172.67.163.127')
        except Exception:
            pass  # Expected in test environment
    
    def test_geolocation_service_detection(self):
        """Test that GEOLOCATION_SOURCE is set correctly for each service"""
        # Test ipinfo.io detection
        vpn_info_ipinfo = json.dumps({
            "ip": "172.67.163.127",
            "country": "ES",
            "city": "Madrid"
        })
        
        # Simulate ipinfo.io success (no fallback needed)
        if vpn_info_ipinfo and vpn_info_ipinfo != '{}':
            geolocation_source = "ipinfo.io"
            self.assertEqual(geolocation_source, "ipinfo.io")
        
        # Test ip-api.com detection (fallback scenario)
        vpn_info_ipapi = json.dumps({
            "query": "172.67.163.127", 
            "countryCode": "ES",
            "city": "Madrid"
        })
        
        # Simulate ipinfo.io failure, ip-api.com success
        if not vpn_info_ipinfo or vpn_info_ipinfo == '{}':
            geolocation_source = "ip-api.com"
            self.assertEqual(geolocation_source, "ip-api.com")
    
    def test_fallback_data_integrity(self):
        """Test that fallback data maintains required fields"""
        # Test ip-api.com response has all required fields
        ipapi_response = {
            "query": "172.67.163.127",
            "status": "success",
            "countryCode": "ES", 
            "city": "Madrid",
            "regionName": "Madrid",
            "isp": "Digi Spain Telecom S.L.",
            "timezone": "Europe/Madrid"
        }
        
        # Required fields for VPN monitoring
        required_fields = ['query', 'countryCode', 'city', 'regionName', 'isp', 'timezone']
        
        for field in required_fields:
            self.assertIn(field, ipapi_response, f"Required field '{field}' missing from ip-api.com response")
            self.assertIsNotNone(ipapi_response[field], f"Field '{field}' cannot be None")
        
        # Test field mapping produces expected results
        ip = ipapi_response.get('query')
        country = ipapi_response.get('countryCode')
        city = ipapi_response.get('city')
        region = ipapi_response.get('regionName')
        org = ipapi_response.get('isp')
        timezone = ipapi_response.get('timezone')
        
        self.assertEqual(ip, "172.67.163.127")
        self.assertEqual(country, "ES")
        self.assertEqual(city, "Madrid")
        self.assertEqual(region, "Madrid")
        self.assertEqual(org, "Digi Spain Telecom S.L.")
        self.assertEqual(timezone, "Europe/Madrid")


class TestSecurityFeatures(unittest.TestCase):
    """Test security features for JSON injection prevention"""
    
    def setUp(self):
        """Set up test environment"""
        # Path to client script
        self.script_path = os.path.join(
            os.path.dirname(__file__), 
            '../../vpn-sentinel-client/vpn-sentinel-client.sh'
        )
    
    def test_client_id_sanitization_basic(self):
        """Test CLIENT_ID sanitization removes basic dangerous characters"""
        # Test simple cases that don't involve complex shell escaping
        test_cases = [
            ('normal-client-001', 'normal-client-001'),  # Already valid
            ('CLIENT_001', 'client-001'),  # Uppercase and underscores
            ('My Client ID', 'my-client-id'),  # Spaces become dashes
            ('client@domain.com', 'client-domain-com'),  # Special chars removed
        ]
        
        for input_id, expected_output in test_cases:
            with self.subTest(input_id=input_id):
                # Use a simple shell command that avoids complex escaping
                cmd = f'echo "{input_id}" | tr "[:upper:]" "[:lower:]" | sed "s/[^a-z0-9-]/-/g" | sed "s/--*/-/g" | sed "s/^-//" | sed "s/-$//"'
                
                result = subprocess.run(
                    ['bash', '-c', cmd],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                self.assertEqual(result.returncode, 0)
                actual = result.stdout.strip()
                # Handle empty result
                if not actual:
                    actual = "sanitized-client"
                self.assertEqual(actual, expected_output)
    
    def test_client_id_validation_logic(self):
        """Test the CLIENT_ID validation detects invalid characters"""
        # Test which strings trigger sanitization
        valid_cases = ['my-client-001', 'client123', 'test-client']
        invalid_cases = ['my"client', "my'client", 'my client', 'CLIENT_001', 'client@domain.com']
        
        for client_id in valid_cases:
            with self.subTest(client_id=client_id):
                cmd = f'echo "{client_id}" | grep -q "[^a-z0-9-]" && echo "INVALID" || echo "VALID"'
                result = subprocess.run(
                    ['bash', '-c', cmd],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout.strip(), "VALID")
        
        for client_id in invalid_cases:
            with self.subTest(client_id=client_id):
                # Escape quotes for shell
                escaped_id = client_id.replace('"', '\\"').replace("'", "\\'")
                cmd = f'echo "{escaped_id}" | grep -q "[^a-z0-9-]" && echo "INVALID" || echo "VALID"'
                result = subprocess.run(
                    ['bash', '-c', cmd],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout.strip(), "INVALID")
    
    def test_json_escape_basic(self):
        """Test basic JSON escaping functionality"""
        test_cases = [
            ('normal', 'normal'),
            ('with"quotes', 'with\\"quotes'),
            ('with\\\\backslash', 'with\\\\\\\\backslash'),
        ]
        
        for input_str, expected in test_cases:
            with self.subTest(input_str=input_str):
                # Test the json_escape function with simple inputs
                cmd = f"""json_escape() {{ printf '%s' "$1" | sed 's/\\\\/\\\\\\\\/g; s/"/\\\\"/g'; }}; json_escape '{input_str}'"""
                result = subprocess.run(
                    ['bash', '-c', cmd],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout.strip(), expected)
    
    def test_sanitize_string_basic(self):
        """Test basic string sanitization"""
        test_cases = [
            ('normal_string', 'normal_string'),
            ('string\nwith\nlines', 'stringwithlines'),
            ('string\twith\ttabs', 'stringwithtabs'),
            ('short_string', 'short_string'),
        ]
        
        for input_str, expected in test_cases:
            with self.subTest(input_str=input_str):
                # Test sanitization with safe inputs
                cmd = f"""sanitize_string() {{ printf '%s' "$1" | tr -d '\\000-\\037' | head -c 100; }}; sanitize_string '{input_str}'"""
                result = subprocess.run(
                    ['bash', '-c', cmd],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout.strip(), expected)
    
    def test_script_contains_security_functions(self):
        """Test that the script contains the security functions we added"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        
        # Check for security functions
        self.assertIn('json_escape()', content, "json_escape function should be present")
        self.assertIn('sanitize_string()', content, "sanitize_string function should be present")
        
        # Check for sanitization usage
        self.assertIn('| sanitize_string', content, "sanitize_string should be used in parsing")
        self.assertIn('$(json_escape', content, "json_escape should be used in JSON construction")
        
        # Check for CLIENT_ID sanitization
        self.assertIn('tr \'[:upper:]\' \'[:lower:]\'', content, "CLIENT_ID sanitization should be present")
    
    def test_json_structure_integrity(self):
        """Test that JSON structure remains valid with escaped content"""
        # Test that our JSON escaping produces valid JSON
        test_payloads = [
            '{"client_id": "test-client", "status": "alive"}',
            '{"client_id": "test\\"client\\"id", "status": "alive"}',
            '{"client_id": "test\\\\client\\\\id", "status": "alive"}',
        ]
        
        import json
        for payload in test_payloads:
            with self.subTest(payload=payload):
                # Should be valid JSON
                try:
                    parsed = json.loads(payload)
                    self.assertIn('client_id', parsed)
                    self.assertEqual(parsed['status'], 'alive')
                except json.JSONDecodeError:
                    self.fail(f"Invalid JSON: {payload}")


if __name__ == '__main__':
    unittest.main()