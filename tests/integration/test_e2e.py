"""Moved: server-dependent E2E tests now live in tests/integration_server.

This file is a harmless shim to avoid accidental execution in CI. To run the
real E2E tests, enable them explicitly:

    export VPN_SENTINEL_SERVER_TESTS=1
    pytest tests/integration_server -q

"""
import os
import subprocess
import time
import unittest
from datetime import datetime, timezone

import pytest
import requests

pytest.skip("Moved to tests/integration_server/ (server-dependent). Set VPN_SENTINEL_SERVER_TESTS=1 to run.", allow_module_level=True)


class TestDockerIntegration(unittest.TestCase):
    """Test Docker-based deployment integration"""
    
    def test_docker_compose_syntax(self):
        """Test Docker Compose file syntax"""
        compose_files = [
            '../../compose.yaml',
            '../../deployments/server-central/compose.yaml',
            '../../deployments/all-in-one/compose.yaml', 
            '../../deployments/client-with-vpn/compose.yaml',
            '../../deployments/client-standalone/compose.yaml'
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
        self.server_url = "http://localhost:5000"
        self.health_url = "http://localhost:8081"
        self.api_path = os.getenv("VPN_SENTINEL_API_PATH", "/api/v1")  # Use environment variable
        self.health_path = "/health"
        self.api_key = "test-api-key-abcdef123456789"  # Match test environment API key
        
    @unittest.skip("Temporarily skipped: investigate client registration workflow later")
    def test_client_registration_workflow(self):
        """Test complete client registration and monitoring workflow"""
        try:
            # Step 1: Health check
            health_response = requests.get(
                f"{self.health_url}{self.health_path}",
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
    
    @unittest.skip("Temporarily skipped: investigate same-IP warning workflow later")
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
            '../../deployments/server-central/.env.example',
            '../../deployments/all-in-one/.env.example',
            '../../deployments/client-with-vpn/.env.example',
            '../../deployments/client-standalone/.env.example'
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
                    
                    # Check server requirements for server deployments only
                    if 'server-only' in env_file or 'unified' in env_file:
                        for var in server_required_vars:
                            self.assertIn(var, content,
                                        f"Server variable {var} not found in {env_file}")

                    # Client-only deployments should have server connection info
                    if 'client-only' in env_file:
                        client_required_vars = [
                            'VPN_SENTINEL_URL',
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