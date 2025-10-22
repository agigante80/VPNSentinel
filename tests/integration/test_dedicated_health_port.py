"""
Integration tests for VPN Sentinel dedicated health port
Tests the new dedicated health server on port 8081
"""
import os
import sys
import unittest
import time
import requests
import subprocess
import signal
from unittest.mock import patch


class TestDedicatedHealthPort(unittest.TestCase):
    """Integration tests for dedicated health port functionality"""

    def setUp(self):
        """Set up integration test environment"""
        self.server_process = None
        self.api_url = "http://localhost:5000"
        self.health_url = "http://localhost:8081"
        self.dashboard_url = "http://localhost:8080"
        self.api_path = "/api/v1"
        self.health_path = "/health"

    def tearDown(self):
        """Clean up after tests"""
        if self.server_process:
            try:
                os.killpg(os.getpgid(self.server_process.pid), signal.SIGTERM)
                self.server_process.wait(timeout=5)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                try:
                    os.killpg(os.getpgid(self.server_process.pid), signal.SIGKILL)
                    self.server_process.wait()
                except ProcessLookupError:
                    pass  # Process already dead

    def start_test_server(self):
        """Start a test instance of the VPN Sentinel server with dedicated health port"""
        try:
            # Get the project root (parent of tests directory)
            test_dir = os.path.dirname(os.path.abspath(__file__))
            tests_dir = os.path.dirname(test_dir)
            project_root = os.path.dirname(tests_dir)

            # Set environment for testing with dedicated health port
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
            time.sleep(5)

            # Check if all servers are responding
            try:
                # Check API server
                api_response = requests.get(f"{self.api_url}{self.api_path}/status", timeout=5)
                # Check health server
                health_response = requests.get(f"{self.health_url}{self.health_path}", timeout=5)
                # Check dashboard server
                dashboard_response = requests.get(f"{self.dashboard_url}/dashboard", timeout=5)

                return (api_response.status_code == 200 and
                       health_response.status_code == 200 and
                       dashboard_response.status_code == 200)
            except requests.RequestException:
                return False

        except Exception as e:
            print(f"Failed to start test server: {e}")
            return False

    def test_dedicated_health_port_basic_functionality(self):
        """Test that dedicated health port serves health endpoints correctly"""
        if not self.start_test_server():
            self.skipTest("Cannot start test server")

        # Test main health endpoint
        response = requests.get(f"{self.health_url}{self.health_path}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('system', data)
        self.assertIn('server_time', data)

        # Test readiness endpoint
        response = requests.get(f"{self.health_url}{self.health_path}/ready")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ready')
        self.assertIn('checks', data)

        # Test startup endpoint
        response = requests.get(f"{self.health_url}{self.health_path}/startup")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'started')
        self.assertIn('server_time', data)

    def test_health_endpoints_no_authentication_required(self):
        """Test that health endpoints work without authentication"""
        if not self.start_test_server():
            self.skipTest("Cannot start test server")

        # Test all health endpoints without any auth headers
        endpoints = [
            f"{self.health_url}{self.health_path}",
            f"{self.health_url}{self.health_path}/ready",
            f"{self.health_url}{self.health_path}/startup"
        ]

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = requests.get(endpoint)
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertIn('status', data)

    def test_api_endpoints_still_on_api_port(self):
        """Test that API endpoints are still served on the API port"""
        if not self.start_test_server():
            self.skipTest("Cannot start test server")

        # Test API status endpoint
        response = requests.get(f"{self.api_url}{self.api_path}/status")
        self.assertEqual(response.status_code, 200)
        # Should return empty JSON object for status when no clients

        # Test that health endpoints are NOT on API port
        response = requests.get(f"{self.api_url}{self.api_path}/health")
        self.assertEqual(response.status_code, 404)

    def test_dashboard_on_dashboard_port(self):
        """Test that dashboard is served on the dashboard port"""
        if not self.start_test_server():
            self.skipTest("Cannot start test server")

        response = requests.get(f"{self.dashboard_url}/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/html', response.headers.get('content-type', ''))

    def test_health_endpoints_wrong_port_returns_404(self):
        """Test that accessing health endpoints on wrong ports returns 404"""
        if not self.start_test_server():
            self.skipTest("Cannot start test server")

        # Health endpoints should not be available on API port
        wrong_endpoints = [
            f"{self.api_url}{self.api_path}/health",
            f"{self.api_url}{self.api_path}/health/ready",
            f"{self.api_url}{self.api_path}/health/startup",
            f"{self.dashboard_url}/health"
        ]

        for endpoint in wrong_endpoints:
            with self.subTest(endpoint=endpoint):
                response = requests.get(endpoint)
                self.assertEqual(response.status_code, 404)

    def test_health_endpoints_wrong_method_returns_405(self):
        """Test that wrong HTTP methods on health endpoints return 405"""
        if not self.start_test_server():
            self.skipTest("Cannot start test server")

        endpoints = [
            f"{self.health_url}{self.health_path}",
            f"{self.health_url}{self.health_path}/ready",
            f"{self.health_url}{self.health_path}/startup"
        ]

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = requests.post(endpoint)
                self.assertEqual(response.status_code, 405)

    def test_health_endpoints_invalid_path_returns_404(self):
        """Test that invalid health paths return 404"""
        if not self.start_test_server():
            self.skipTest("Cannot start test server")

        invalid_endpoints = [
            f"{self.health_url}{self.health_path}/invalid",
            f"{self.health_url}/invalid/health",
            f"{self.health_url}/api/v1/health"
        ]

        for endpoint in invalid_endpoints:
            with self.subTest(endpoint=endpoint):
                response = requests.get(endpoint)
                self.assertEqual(response.status_code, 404)

    def test_health_server_isolation(self):
        """Test that health server is completely isolated from API server"""
        if not self.start_test_server():
            self.skipTest("Cannot start test server")

        # Health server should not serve API endpoints
        api_endpoints_on_health_port = [
            f"{self.health_url}{self.api_path}/status",
            f"{self.health_url}{self.api_path}/keepalive",
            f"{self.health_url}/dashboard"
        ]

        for endpoint in api_endpoints_on_health_port:
            with self.subTest(endpoint=endpoint):
                response = requests.get(endpoint)
                self.assertEqual(response.status_code, 404)

    def test_health_endpoints_response_format(self):
        """Test that health endpoints return proper JSON responses"""
        if not self.start_test_server():
            self.skipTest("Cannot start test server")

        # Test main health endpoint response structure
        response = requests.get(f"{self.health_url}{self.health_path}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['content-type'], 'application/json')

        data = response.json()
        required_fields = ['status', 'server_time', 'active_clients', 'uptime_info', 'system']
        for field in required_fields:
            self.assertIn(field, data)

        # Test readiness endpoint response structure
        response = requests.get(f"{self.health_url}{self.health_path}/ready")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('status', data)
        self.assertIn('checks', data)

        # Test startup endpoint response structure
        response = requests.get(f"{self.health_url}{self.health_path}/startup")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('status', data)
        self.assertIn('server_time', data)
        self.assertIn('uptime_info', data)

    def test_health_endpoints_cors_headers(self):
        """Test that health endpoints include appropriate CORS headers if needed"""
        if not self.start_test_server():
            self.skipTest("Cannot start test server")

        response = requests.get(f"{self.health_url}{self.health_path}")
        # CORS headers might not be set for health endpoints (by design)
        # This test ensures we don't accidentally add CORS to health endpoints
        cors_headers = ['access-control-allow-origin', 'access-control-allow-methods']
        for header in cors_headers:
            self.assertNotIn(header, response.headers)


if __name__ == '__main__':
    unittest.main()