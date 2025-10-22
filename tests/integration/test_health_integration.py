"""
Integration tests for VPN Sentinel health checks
Tests health check endpoints in a more realistic environment
"""
import os
import sys
import unittest
import time
import requests
import subprocess
import signal
from unittest.mock import patch


class TestHealthCheckIntegration(unittest.TestCase):
    """Integration tests for health check functionality"""

    def setUp(self):
        """Set up integration test environment"""
        self.server_process = None
        self.server_url = "http://localhost:5000"
        self.health_url = "http://localhost:8081"
        self.api_path = "/api/v1"
        self.health_path = "/health"

    def tearDown(self):
        """Clean up after tests"""
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                self.server_process.wait()

    def start_test_server(self):
        """Start a test instance of the VPN Sentinel server"""
        try:
            # Get the project root (parent of tests directory)
            test_dir = os.path.dirname(os.path.abspath(__file__))
            tests_dir = os.path.dirname(test_dir)
            project_root = os.path.dirname(tests_dir)
            
            # Set minimal environment for testing
            env = os.environ.copy()
            env.update({
                'VPN_SENTINEL_API_PATH': self.api_path,
                'VPN_SENTINEL_HEALTH_PATH': self.health_path,
                'VPN_SENTINEL_SERVER_API_PORT': '5000',
                'VPN_SENTINEL_SERVER_HEALTH_PORT': '8081',
                'VPN_SENTINEL_SERVER_DASHBOARD_PORT': '8080',
                'FLASK_ENV': 'testing',
                'PYTHONPATH': os.path.join(project_root, 'vpn-sentinel-server'),
                'WEB_DASHBOARD_ENABLED': 'true'
            })

            # Start server in background
            self.server_process = subprocess.Popen(
                [sys.executable, os.path.join(project_root, 'vpn-sentinel-server', 'vpn-sentinel-server.py')],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )

            # Wait for server to start
            time.sleep(3)

            # Check if server is responding
            try:
                # Check both API and health servers
                api_response = requests.get(f"{self.server_url}{self.api_path}/status", timeout=5)
                health_response = requests.get(f"{self.health_url}{self.health_path}", timeout=5)
                return api_response.status_code == 200 and health_response.status_code == 200
            except requests.RequestException:
                return False

        except Exception as e:
            print(f"Failed to start test server: {e}")
            return False

    @unittest.skip("Requires running server - use for manual integration testing")
    def test_server_health_endpoints_integration(self):
        """Integration test for all server health endpoints"""
        if not self.start_test_server():
            self.skipTest("Cannot start test server")

        # Test liveness endpoint on dedicated health port
        response = requests.get(f"{self.health_url}{self.health_path}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('system', data)
        self.assertIn('dependencies', data)

        # Test readiness endpoint on dedicated health port
        response = requests.get(f"{self.health_url}{self.health_path}/ready")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ready')
        self.assertIn('checks', data)

        # Test startup endpoint on dedicated health port
        response = requests.get(f"{self.health_url}{self.health_path}/startup")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'started')

    @unittest.skip("Requires Docker - use for manual integration testing")
    def test_client_health_check_integration(self):
        """Integration test for client health check script"""
        # This test requires a running client container
        # Run: docker run -d --name test-client vpn-sentinel/client:latest

        script_path = "../../vpn-sentinel-client/healthcheck.sh"

        # Test health check script directly
        result = subprocess.run([script_path], capture_output=True, text=True)

        # Should succeed if client is running properly
        self.assertEqual(result.returncode, 0)
        self.assertIn('✅ VPN Sentinel client is healthy', result.stdout)

    def test_health_check_script_exists(self):
        """Test that health check script exists and is executable"""
        # Get the project root (parent of tests directory)
        test_dir = os.path.dirname(os.path.abspath(__file__))
        tests_dir = os.path.dirname(test_dir)
        project_root = os.path.dirname(tests_dir)
        script_path = os.path.join(project_root, "vpn-sentinel-client", "healthcheck.sh")

        self.assertTrue(os.path.exists(script_path))
        self.assertTrue(os.access(script_path, os.X_OK))

        # Test script help/version
        result = subprocess.run([script_path], capture_output=True, text=True, timeout=10)

        # Script should run and produce output
        self.assertIsNotNone(result.stdout)

    def test_server_dockerfile_healthcheck_configuration(self):
        """Test that server Dockerfile has proper HEALTHCHECK configuration"""
        # Get the project root (parent of tests directory)
        test_dir = os.path.dirname(os.path.abspath(__file__))
        tests_dir = os.path.dirname(test_dir)
        project_root = os.path.dirname(tests_dir)
        dockerfile_path = os.path.join(project_root, "vpn-sentinel-server", "Dockerfile")

        with open(dockerfile_path, 'r') as f:
            content = f.read()

        # Should contain HEALTHCHECK instruction
        self.assertIn('HEALTHCHECK', content)
        self.assertIn('curl', content)
        self.assertIn('8081', content)  # Health port instead of API port
        self.assertIn('/health', content)  # Health path

        # Should have proper timing parameters
        self.assertIn('--interval=', content)
        self.assertIn('--timeout=', content)

    def test_client_dockerfile_healthcheck_configuration(self):
        """Test that client Dockerfile has proper HEALTHCHECK configuration"""
        # Get the project root (parent of tests directory)
        test_dir = os.path.dirname(os.path.abspath(__file__))
        tests_dir = os.path.dirname(test_dir)
        project_root = os.path.dirname(tests_dir)
        dockerfile_path = os.path.join(project_root, "vpn-sentinel-client", "Dockerfile")

        with open(dockerfile_path, 'r') as f:
            content = f.read()

        # Should contain HEALTHCHECK instruction
        self.assertIn('HEALTHCHECK', content)
        self.assertIn('healthcheck.sh', content)

        # Should have proper timing parameters
        self.assertIn('--interval=', content)
        self.assertIn('--timeout=', content)

    def test_health_check_script_in_dockerfile(self):
        """Test that health check script is properly included in client Dockerfile"""
        # Get the project root (parent of tests directory)
        test_dir = os.path.dirname(os.path.abspath(__file__))
        tests_dir = os.path.dirname(test_dir)
        project_root = os.path.dirname(tests_dir)
        dockerfile_path = os.path.join(project_root, "vpn-sentinel-client", "Dockerfile")
        script_path = os.path.join(project_root, "vpn-sentinel-client", "healthcheck.sh")

        with open(dockerfile_path, 'r') as f:
            content = f.read()

        # Should copy the health check script
        self.assertIn('COPY healthcheck.sh', content)
        self.assertIn('chmod +x /app/healthcheck.sh', content)

        # Script should exist
        self.assertTrue(os.path.exists(script_path))

    def test_server_health_endpoints_documentation(self):
        """Test that server code properly documents health endpoints"""
        # Get the project root (parent of tests directory)
        test_dir = os.path.dirname(os.path.abspath(__file__))
        tests_dir = os.path.dirname(test_dir)
        project_root = os.path.dirname(tests_dir)
        server_file = os.path.join(project_root, "vpn-sentinel-server", "vpn-sentinel-server.py")

        with open(server_file, 'r') as f:
            content = f.read()

        # Should document all health endpoints on api_app using API_PATH
        self.assertIn("@api_app.route(f'{API_PATH}/health', methods=['GET'])", content)
        self.assertIn("@api_app.route(f'{API_PATH}/health/ready', methods=['GET'])", content)
        self.assertIn("@api_app.route(f'{API_PATH}/health/startup', methods=['GET'])", content)

        # Should have docstrings
        self.assertIn('def health(', content)
        self.assertIn('def readiness(', content)
        self.assertIn('def startup(', content)