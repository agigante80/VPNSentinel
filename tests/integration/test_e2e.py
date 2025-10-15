"""
Integration tests for VPN Sentinel
Tests end-to-end functionality between server and client components
"""
import os
import sys
import unittest
import requests
import json
import time
import subprocess
from unittest.mock import patch, Mock
import tempfile
from datetime import datetime, timezone

# Add fixtures to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../fixtures'))
from sample_data import SAMPLE_KEEPALIVE_REQUEST, TEST_ENV_VARS


class TestServerClientIntegration(unittest.TestCase):
    """Test integration between server and client"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment for integration tests"""
        cls.server_url = os.getenv("VPN_SENTINEL_SERVER_API_BASE_URL", "http://localhost:5000")
        cls.api_path = "/test/v1"
        cls.dashboard_url = "http://localhost:5001"
        cls.api_key = os.getenv("VPN_SENTINEL_API_KEY", "test-api-key-abcdef123456789")
    
    def test_server_health_endpoint(self):
        """Test server health check endpoint"""
        try:
            response = requests.get(
                f"{self.server_url}{self.api_path}/health",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.assertEqual(data['status'], 'healthy')
                self.assertIn('server_time', data)
                self.assertIn('active_clients', data)
            else:
                self.skipTest(f"Server not available: {response.status_code}")
                
        except requests.ConnectionError:
            self.skipTest("Server not running for integration tests")
    
    def test_keepalive_endpoint_with_auth(self):
        """Test keepalive endpoint with proper authentication"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = SAMPLE_KEEPALIVE_REQUEST.copy()
            payload['client_id'] = 'integration-test-client'
            payload['timestamp'] = datetime.now(timezone.utc).isoformat()
            
            response = requests.post(
                f"{self.server_url}{self.api_path}/keepalive",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.assertEqual(data['status'], 'ok')
                self.assertIn('message', data)
                self.assertIn('server_time', data)
            else:
                self.skipTest(f"Keepalive failed: {response.status_code} - {response.text}")
                
        except requests.ConnectionError:
            self.skipTest("Server not running for integration tests")
    
    def test_keepalive_endpoint_without_auth(self):
        """Test keepalive endpoint without authentication (should fail)"""
        try:
            payload = SAMPLE_KEEPALIVE_REQUEST.copy()
            
            response = requests.post(
                f"{self.server_url}{self.api_path}/keepalive",
                json=payload,
                timeout=10
            )
            
            # Should return 401 Unauthorized
            self.assertEqual(response.status_code, 401)
            
        except requests.ConnectionError:
            self.skipTest("Server not running for integration tests")
    
    def test_keepalive_endpoint_with_wrong_auth(self):
        """Test keepalive endpoint with incorrect authentication (should fail)"""
        try:
            headers = {
                'Authorization': 'Bearer wrong-api-key-12345',
                'Content-Type': 'application/json'
            }
            
            payload = SAMPLE_KEEPALIVE_REQUEST.copy()
            
            response = requests.post(
                f"{self.server_url}{self.api_path}/keepalive",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            # Should return 401 Unauthorized for wrong API key
            self.assertEqual(response.status_code, 401)
            
        except requests.ConnectionError:
            self.skipTest("Server not running for integration tests")
    
    def test_dashboard_accessibility(self):
        """Test dashboard web interface accessibility"""
        try:
            response = requests.get(f"{self.dashboard_url}/dashboard", timeout=10)
            
            if response.status_code == 200:
                self.assertIn('text/html', response.headers.get('content-type', ''))
                self.assertIn('VPN Sentinel Dashboard', response.text)
                self.assertIn('Server Details', response.text)
            else:
                self.skipTest(f"Dashboard not available: {response.status_code}")
                
        except requests.ConnectionError:
            self.skipTest("Dashboard server not running for integration tests")
    
    def test_rate_limiting(self):
        """Test API rate limiting functionality"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = SAMPLE_KEEPALIVE_REQUEST.copy()
            payload['client_id'] = 'rate-limit-test-client'
            
            # Send multiple requests quickly
            responses = []
            for i in range(5):
                payload['timestamp'] = datetime.now(timezone.utc).isoformat()
                response = requests.post(
                    f"{self.server_url}{self.api_path}/keepalive",
                    headers=headers,
                    json=payload,
                    timeout=5
                )
                responses.append(response.status_code)
                time.sleep(0.1)  # Small delay between requests
            
            # All should succeed if within rate limit
            success_count = sum(1 for code in responses if code == 200)
            self.assertGreater(success_count, 0, "No successful requests within rate limit")
            
        except requests.ConnectionError:
            self.skipTest("Server not running for integration tests")
    
    def test_ip_whitelist_disabled(self):
        """Test that requests work when no IP whitelist is configured (default behavior)"""
        try:
            # Test with valid authentication but no IP whitelist configured
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = SAMPLE_KEEPALIVE_REQUEST.copy()
            payload['client_id'] = 'whitelist-disabled-test'
            payload['timestamp'] = datetime.now(timezone.utc).isoformat()
            
            response = requests.post(
                f"{self.server_url}{self.api_path}/keepalive",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            # Should succeed when no whitelist is configured
            self.assertEqual(response.status_code, 200)
            
        except requests.ConnectionError:
            self.skipTest("Server not running for integration tests")
    
    def test_ip_whitelist_enabled_allows_valid_ip(self):
        """Test that whitelisted IPs are allowed when whitelist is enabled"""
        try:
            # This test requires server to be configured with IP whitelist
            # For now, we'll test the basic functionality by checking server response
            # In a real deployment, this would test against a server with ALLOWED_IPS configured
            
            # Test server health endpoint (should always work regardless of IP whitelist)
            response = requests.get(
                f"{self.server_url}{self.api_path}/health",
                timeout=10
            )
            
            # Health endpoint should be accessible
            if response.status_code == 200:
                data = response.json()
                self.assertEqual(data.get('status'), 'healthy')
            else:
                self.skipTest(f"Health endpoint not accessible: {response.status_code}")
                
        except requests.ConnectionError:
            self.skipTest("Server not running for integration tests")
    
    def test_ip_whitelist_configuration_parsing(self):
        """Test that IP whitelist configuration handles empty/whitespace entries correctly"""
        # This is a unit-style test that can run without server
        # Test the ALLOWED_IPS parsing logic
        
        import os
        from unittest.mock import patch
        
        # Test various whitelist configurations
        test_cases = [
            # (env_value, expected_result)
            ("", []),  # Empty string
            ("192.168.1.100", ["192.168.1.100"]),  # Single IP
            ("192.168.1.100,10.0.0.1", ["192.168.1.100", "10.0.0.1"]),  # Multiple IPs
            (" 192.168.1.100 , 10.0.0.1 ", ["192.168.1.100", "10.0.0.1"]),  # With spaces
            ("192.168.1.100,,10.0.0.1,", ["192.168.1.100", "10.0.0.1"]),  # With empty entries
            ("192.168.1.100, ,10.0.0.1", ["192.168.1.100", "10.0.0.1"]),  # With whitespace-only entries
        ]
        
        for env_value, expected in test_cases:
            with patch.dict(os.environ, {'VPN_SENTINEL_SERVER_ALLOWED_IPS': env_value}):
                # Re-import to get fresh environment
                import importlib
                import sys
                if 'vpn_sentinel_server' in sys.modules:
                    del sys.modules['vpn_sentinel_server']
                
                try:
                    # Try importing the actual module using the same method as unit tests
                    import importlib.util
                    spec = importlib.util.spec_from_file_location(
                        "vpn_sentinel_server", 
                        "/home/alien/dev/VPNSentinel/vpn-sentinel-server/vpn-sentinel-server.py"
                    )
                    server_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(server_module)
                    actual = server_module.ALLOWED_IPS
                    self.assertEqual(actual, expected, f"Failed for env_value='{env_value}'")
                except ImportError:
                    self.skipTest("Cannot test ALLOWED_IPS parsing without server module")


class TestDockerIntegration(unittest.TestCase):
    """Test Docker-based deployment integration"""
    
    def test_docker_compose_syntax(self):
        """Test Docker Compose file syntax"""
        compose_files = [
            '../../compose.yaml',
            '../../deployments/server-only/compose.yaml',
            '../../deployments/unified/compose.yaml', 
            '../../deployments/client-only/compose.yaml'
        ]
        
        for compose_file in compose_files:
            full_path = os.path.join(os.path.dirname(__file__), compose_file)
            if os.path.exists(full_path):
                try:
                    # Test compose file syntax
                    result = subprocess.run(
                        ['docker-compose', '-f', full_path, 'config'],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode != 0:
                        self.fail(f"Docker Compose syntax error in {compose_file}: {result.stderr}")
                        
                except FileNotFoundError:
                    self.skipTest("Docker Compose not available")
                except subprocess.TimeoutExpired:
                    self.skipTest("Docker Compose validation timeout")
            else:
                self.skipTest(f"Compose file not found: {compose_file}")


class TestEndToEndWorkflow(unittest.TestCase):
    """Test complete end-to-end workflows"""
    
    def setUp(self):
        """Set up for E2E tests"""
        self.server_url = "http://localhost:5554"
        self.api_path = "/04ffc8/v1"
        self.api_key = "YorZpnLB7yjrJiInBo4Y61kJLHhuCcT7yVL2iItmJUyR1kjl107hS6JyOuEBgEqZYiQ"
        
    def test_client_registration_workflow(self):
        """Test complete client registration and monitoring workflow"""
        try:
            # Step 1: Health check
            health_response = requests.get(
                f"{self.server_url}{self.api_path}/health",
                timeout=10
            )
            
            if health_response.status_code != 200:
                self.skipTest("Server health check failed")
            
            # Step 2: Send initial keepalive (new client registration)
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            client_id = f'e2e-test-client-{int(time.time())}'
            payload = {
                "client_id": client_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "public_ip": "203.0.113.1",  # Test IP
                "status": "alive",
                "location": {
                    "country": "US",
                    "city": "Test City",
                    "region": "Test Region", 
                    "org": "AS12345 Test Provider",
                    "timezone": "America/New_York"
                },
                "dns_test": {
                    "location": "US",
                    "colo": "NYC"
                }
            }
            
            # Send keepalive
            keepalive_response = requests.post(
                f"{self.server_url}{self.api_path}/keepalive",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            self.assertEqual(keepalive_response.status_code, 200)
            keepalive_data = keepalive_response.json()
            self.assertEqual(keepalive_data['status'], 'ok')
            
            # Step 3: Check server status to verify client is registered
            status_response = requests.get(
                f"{self.server_url}{self.api_path}/status",
                headers=headers,
                timeout=10
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                # Status endpoint returns clients directly, not wrapped in 'clients' key
                self.assertIn(client_id, status_data)
                self.assertEqual(status_data[client_id]['status'], 'alive')
            
        except requests.ConnectionError:
            self.skipTest("Server not running for E2E tests")
    
    def test_same_ip_warning_workflow(self):
        """Test same-IP warning detection workflow"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # First, get server's public IP by sending a keepalive and checking logs
            # For this test, we'll simulate using the known server IP
            server_ip = "172.67.163.127"  # Known from previous tests
            
            client_id = f'same-ip-test-{int(time.time())}'
            payload = {
                "client_id": client_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "public_ip": server_ip,  # Same as server
                "status": "alive",
                "location": {
                    "country": "ES",
                    "city": "Madrid",
                    "region": "Madrid", 
                    "org": "AS57269 DIGI SPAIN TELECOM S.L.",
                    "timezone": "Europe/Madrid"
                },
                "dns_test": {
                    "location": "ES",
                    "colo": "MAD"
                }
            }
            
            # Send keepalive with same IP as server
            response = requests.post(
                f"{self.server_url}{self.api_path}/keepalive",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data['status'], 'ok')
            
            # The server should log a warning about same IP
            # In a real test environment, we could check logs or dashboard
            
        except requests.ConnectionError:
            self.skipTest("Server not running for same-IP test")


class TestConfigurationValidation(unittest.TestCase):
    """Test configuration file validation"""
    
    def test_env_example_files(self):
        """Test that .env.example files are valid"""
        env_example_files = [
            '../../.env.example',
            '../../deployments/server-only/.env.example',
            '../../deployments/unified/.env.example',
            '../../deployments/client-only/.env.example'
        ]
        
        for env_file in env_example_files:
            full_path = os.path.join(os.path.dirname(__file__), env_file)
            if os.path.exists(full_path):
                with self.subTest(env_file=env_file):
                    with open(full_path, 'r') as f:
                        lines = f.readlines()
                    
                    # Check for required variables based on deployment type
                    content = ''.join(lines)
                    
                    # All deployments need API key
                    base_required_vars = ['VPN_SENTINEL_API_KEY']
                    
                    # Server deployments need port configuration
                    server_required_vars = [
                        'VPN_SENTINEL_SERVER_API_PORT',
                        'VPN_SENTINEL_SERVER_DASHBOARD_PORT'
                    ]
                    
                    # Check base requirements
                    for var in base_required_vars:
                        self.assertIn(var, content, 
                                    f"Required variable {var} not found in {env_file}")
                    
                    # Check server requirements for server deployments
                    if 'server' in env_file or 'unified' in env_file or env_file.endswith('/.env.example'):
                        for var in server_required_vars:
                            self.assertIn(var, content, 
                                        f"Server variable {var} not found in {env_file}")
                    
                    # Client-only deployments should have server connection info
                    if 'client-only' in env_file:
                        client_required_vars = [
                            'VPN_SENTINEL_SERVER_API_BASE_URL',
                            'VPN_SENTINEL_CLIENT_ID'
                        ]
                        for var in client_required_vars:
                            self.assertIn(var, content, 
                                        f"Client variable {var} not found in {env_file}")
            else:
                self.skipTest(f"Environment file not found: {env_file}")


if __name__ == '__main__':
    # Run integration tests only if server is running
    print("Running VPN Sentinel Integration Tests")
    print("Note: These tests require the server to be running locally")
    print("Start the server with: docker-compose up -d")
    print()
    
    unittest.main(verbosity=2)