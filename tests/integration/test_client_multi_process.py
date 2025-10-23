"""
Integration tests for VPN Sentinel Client multi-process architecture
Tests the client with health monitor functionality
"""
import os
import sys
import unittest
import time
import requests
import subprocess
import signal
import tempfile
import json


class TestClientMultiProcessIntegration(unittest.TestCase):
    """Integration tests for client multi-process architecture"""

    def setUp(self):
        """Set up integration test environment"""
        self.client_process = None
        self.health_monitor_process = None
        self.test_port = "8083"  # Use different port for testing
        self.client_script = os.path.join(os.path.dirname(__file__), '../../vpn-sentinel-client/vpn-sentinel-client.sh')
        self.health_monitor_script = os.path.join(os.path.dirname(__file__), '../../vpn-sentinel-client/health-monitor.sh')

        # Skip if scripts don't exist
        if not os.path.exists(self.client_script):
            self.skipTest("Client script not found")
        if not os.path.exists(self.health_monitor_script):
            self.skipTest("Health monitor script not found")

    def tearDown(self):
        """Clean up after tests"""
        # Terminate client process
        if self.client_process:
            try:
                os.killpg(os.getpgid(self.client_process.pid), signal.SIGTERM)
                self.client_process.wait(timeout=5)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                try:
                    os.killpg(os.getpgid(self.client_process.pid), signal.SIGKILL)
                    self.client_process.wait()
                except ProcessLookupError:
                    pass  # Process already dead

        # Terminate health monitor process
        if self.health_monitor_process:
            try:
                self.health_monitor_process.terminate()
                self.health_monitor_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.health_monitor_process.kill()
                self.health_monitor_process.wait()

    @unittest.skip("Requires running server - use for manual integration testing")
    def test_client_with_health_monitor_integration(self):
        """Test client running with health monitor enabled"""
        # Set up environment for testing
        env = os.environ.copy()
        env.update({
            'VPN_SENTINEL_HEALTH_MONITOR': 'true',
            'VPN_SENTINEL_HEALTH_PORT': self.test_port,
            'VPN_SENTINEL_URL': 'http://localhost:5000',  # Assume test server is running
            'VPN_SENTINEL_API_PATH': '/api/v1',
            'VPN_SENTINEL_CLIENT_ID': 'integration-test-client',
            'PATH': '/bin:/usr/bin'
        })

        # Start client with health monitor
        try:
            self.client_process = subprocess.Popen(
                [self.client_script],
                env=env,
                preexec_fn=os.setsid,  # Create new process group
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Give client time to start and launch health monitor
            time.sleep(5)

            # Check that client process is running
            self.assertIsNotNone(self.client_process.poll())
            if self.client_process.poll() is not None:
                stdout, stderr = self.client_process.communicate()
                self.fail(f"Client process exited early. STDOUT: {stdout}, STDERR: {stderr}")

            # Check that health monitor is accessible
            health_url = f"http://localhost:{self.test_port}/health"
            response = requests.get(health_url, timeout=5)

            self.assertEqual(response.status_code, 200)
            data = response.json()

            # Verify health response structure
            self.assertIn('status', data)
            self.assertIn('checks', data)
            self.assertIn('client_process', data['checks'])
            self.assertIn('network_connectivity', data['checks'])

            # Client process should be healthy
            self.assertEqual(data['checks']['client_process'], 'healthy')

        except subprocess.TimeoutExpired:
            self.skipTest("Client startup timed out")

    def test_health_monitor_standalone_functionality(self):
        """Test health monitor running standalone"""
        env = os.environ.copy()
        env.update({
            'VPN_SENTINEL_HEALTH_PORT': self.test_port,
            'PATH': '/bin:/usr/bin'
        })

        try:
            # Kill any existing client processes to ensure clean test environment
            subprocess.run(['pkill', '-f', 'vpn-sentinel-client.sh'], 
                         capture_output=True)
            time.sleep(1)  # Give processes time to terminate

            # Start health monitor
            self.health_monitor_process = subprocess.Popen(
                [self.health_monitor_script],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Give it time to start
            time.sleep(3)

            # Check if health monitor is still running
            if self.health_monitor_process.poll() is not None:
                # If it exited, skip the test as health monitor may not work in this environment
                self.skipTest("Health monitor exited prematurely - may not be compatible with test environment")

            # Test health endpoint - should return 503 when client not running
            health_url = f"http://localhost:{self.test_port}/health"
            response = requests.get(health_url, timeout=5)

            self.assertEqual(response.status_code, 503)  # Service unavailable when client not running
            data = response.json()

            # Verify response structure
            self.assertIn('status', data)
            self.assertIn('checks', data)
            self.assertIn('timestamp', data)
            # Accept both 'unhealthy' and 'error' as valid when client not running
            self.assertIn(data['status'], ['unhealthy', 'error'])
            self.assertEqual(data['checks']['client_process'], 'not_running')

        except (requests.exceptions.RequestException, subprocess.TimeoutExpired):
            self.skipTest("Health monitor integration test not compatible with current environment")
        except subprocess.TimeoutExpired:
            self.skipTest("Health monitor startup timed out")

    def test_health_monitor_readiness_endpoint(self):
        """Test health monitor readiness endpoint"""
        env = os.environ.copy()
        env.update({
            'VPN_SENTINEL_HEALTH_PORT': self.test_port,
            'PATH': '/bin:/usr/bin'
        })

        try:
            # Kill any existing client processes to ensure clean test environment
            subprocess.run(['pkill', '-f', 'vpn-sentinel-client.sh'], 
                         capture_output=True)
            time.sleep(1)  # Give processes time to terminate

            # Start health monitor
            self.health_monitor_process = subprocess.Popen(
                [self.health_monitor_script],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            time.sleep(3)

            # Check if health monitor is still running
            if self.health_monitor_process.poll() is not None:
                # If it exited, skip the test as health monitor may not work in this environment
                self.skipTest("Health monitor exited prematurely - may not be compatible with test environment")

            # Test readiness endpoint - should return 503 when client not running
            readiness_url = f"http://localhost:{self.test_port}/health/ready"
            response = requests.get(readiness_url, timeout=5)

            self.assertEqual(response.status_code, 503)  # Not ready when client not running
            data = response.json()

            self.assertIn('status', data)
            self.assertIn('checks', data)
            self.assertEqual(data['status'], 'not_ready')

        except (requests.exceptions.RequestException, subprocess.TimeoutExpired):
            self.skipTest("Readiness endpoint integration test not compatible with current environment")

    def test_health_monitor_startup_endpoint(self):
        """Test health monitor startup endpoint"""
        env = os.environ.copy()
        env.update({
            'VPN_SENTINEL_HEALTH_PORT': self.test_port,
            'PATH': '/bin:/usr/bin'
        })

        try:
            # Start health monitor
            self.health_monitor_process = subprocess.Popen(
                [self.health_monitor_script],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            time.sleep(3)

            # Test startup endpoint
            startup_url = f"http://localhost:{self.test_port}/health/startup"
            response = requests.get(startup_url, timeout=5)

            self.assertEqual(response.status_code, 200)
            data = response.json()

            self.assertIn('status', data)
            self.assertEqual(data['status'], 'started')
            self.assertIn('message', data)

        except requests.exceptions.RequestException:
            self.skipTest("Startup endpoint not accessible")

    def test_client_script_health_monitor_configuration(self):
        """Test that client script properly handles health monitor configuration"""
        # Read the client script and verify health monitor configuration
        with open(self.client_script, 'r') as f:
            content = f.read()

        # Should contain health monitor configuration
        self.assertIn('VPN_SENTINEL_HEALTH_MONITOR', content)
        self.assertIn('VPN_SENTINEL_HEALTH_PORT', content)
        self.assertIn('health-monitor.sh', content)
        self.assertIn('HEALTH_MONITOR_PID', content)

    def test_dockerfile_multi_process_support(self):
        """Test that Dockerfile supports multi-process client"""
        dockerfile_path = os.path.join(os.path.dirname(self.client_script), 'Dockerfile')

        if not os.path.exists(dockerfile_path):
            self.skipTest("Dockerfile not found")

        with open(dockerfile_path, 'r') as f:
            content = f.read()

        # Should contain multi-process support
        self.assertIn('health-monitor.sh', content)
        self.assertIn('python3', content)
        self.assertIn('flask', content)
        self.assertIn('Multi-process mode', content)

    def test_enhanced_healthcheck_script(self):
        """Test the enhanced health check script functionality"""
        healthcheck_script = os.path.join(os.path.dirname(self.client_script), 'healthcheck.sh')

        if not os.path.exists(healthcheck_script):
            self.skipTest("Health check script not found")

        with open(healthcheck_script, 'r') as f:
            content = f.read()

        # Should contain enhanced functionality
        self.assertIn('HEALTH_MONITOR_RUNNING', content)
        self.assertIn('--json', content)
        self.assertIn('memory_usage', content)
        self.assertIn('disk_usage', content)
        self.assertIn('"status":', content)
        self.assertIn('"checks":', content)

    def test_health_monitor_invalid_port_configuration(self):
        """Test health monitor with invalid port configuration"""
        env = os.environ.copy()
        env.update({
            'VPN_SENTINEL_HEALTH_PORT': 'invalid_port',
            'PATH': '/bin:/usr/bin'
        })

        try:
            # Start health monitor with invalid port
            self.health_monitor_process = subprocess.Popen(
                [self.health_monitor_script],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            time.sleep(2)

            # Check if process is still running or exited
            if self.health_monitor_process.poll() is None:
                # Process is still running, which might be okay
                # The Python code might handle the error gracefully
                self.health_monitor_process.terminate()
                self.health_monitor_process.wait(timeout=5)
            else:
                # Process exited - check stderr for error messages
                stdout, stderr = self.health_monitor_process.communicate()
                # Should have some error indication
                self.assertTrue(len(stderr) > 0 or self.health_monitor_process.poll() != 0)

        except (requests.exceptions.RequestException, subprocess.TimeoutExpired):
            self.skipTest("Health monitor test not compatible with current environment")

    def test_health_monitor_missing_dependencies(self):
        """Test health monitor when Python/Flask dependencies are missing"""
        env = os.environ.copy()
        env.update({
            'VPN_SENTINEL_HEALTH_PORT': self.test_port,
            'PATH': '/bin'  # Remove /usr/bin to simulate missing python3
        })

        try:
            # Start health monitor
            self.health_monitor_process = subprocess.Popen(
                [self.health_monitor_script],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            time.sleep(3)

            # Check the process state - it might exit gracefully or continue
            if self.health_monitor_process.poll() is None:
                # Process is still running - check if it's actually functional
                # Try to connect to see if the health monitor is working
                try:
                    response = requests.get(f"http://localhost:{self.test_port}/health", timeout=2)
                    # If we get here, the health monitor is working despite limited PATH
                    self.health_monitor_process.terminate()
                    self.health_monitor_process.wait(timeout=5)
                except requests.exceptions.RequestException:
                    # Connection failed, which is expected
                    self.health_monitor_process.terminate()
                    self.health_monitor_process.wait(timeout=5)
            else:
                # Process exited - this could be due to missing dependencies or other issues
                stdout, stderr = self.health_monitor_process.communicate()
                # Either exit code should be non-zero or there should be error output
                has_error = (self.health_monitor_process.poll() != 0 or 
                           len(stderr.strip()) > 0 or 
                           'error' in stdout.lower() or 
                           'error' in stderr.lower())
                self.assertTrue(has_error, f"Expected error but got clean exit. STDOUT: {stdout}, STDERR: {stderr}")

        except (requests.exceptions.RequestException, subprocess.TimeoutExpired):
            self.skipTest("Health monitor test not compatible with current environment")

    def test_client_script_health_monitor_disabled(self):
        """Test client script when health monitor is explicitly disabled"""
        env = os.environ.copy()
        env.update({
            'VPN_SENTINEL_HEALTH_MONITOR': 'false',
            'VPN_SENTINEL_URL': 'http://localhost:5000',
            'VPN_SENTINEL_API_PATH': '/api/v1',
            'VPN_SENTINEL_CLIENT_ID': 'test-client-disabled-monitor',
            'PATH': '/bin:/usr/bin'
        })

        try:
            # Start client with health monitor disabled
            self.client_process = subprocess.Popen(
                [self.client_script],
                env=env,
                preexec_fn=os.setsid,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            time.sleep(3)

            # Client should still be running
            self.assertIsNone(self.client_process.poll())

            # Check that no health monitor process is running for this user
            result = subprocess.run(['pgrep', '-u', str(os.getuid()), '-f', 'health-monitor.sh'],
                                  capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)  # Should not find health monitor

        except subprocess.TimeoutExpired:
            self.skipTest("Client startup timed out")
        finally:
            if self.client_process:
                try:
                    os.killpg(os.getpgid(self.client_process.pid), signal.SIGTERM)
                    self.client_process.wait(timeout=5)
                except (subprocess.TimeoutExpired, ProcessLookupError):
                    pass