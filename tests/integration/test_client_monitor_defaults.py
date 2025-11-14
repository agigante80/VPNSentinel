"""
Integration tests for VPN Sentinel client monitor default behavior
Covers:
- Default behavior: when VPN_SENTINEL_HEALTH_MONITOR is unset, the client should spawn the health monitor
- Disabled behavior: when VPN_SENTINEL_HEALTH_MONITOR=false, health endpoints should be unavailable

These tests are designed to be lightweight and skip gracefully in constrained CI environments.
"""
import os
import time
import subprocess
import signal
import requests
from tests.helpers import probe_url, start_client_with_monitor, stop_client_process, kill_health_monitor_processes, ensure_scripts_exist, assert_health_schema
import unittest


class TestClientMonitorDefaults(unittest.TestCase):
    def setUp(self):
        self.client_process = None
        self.test_port = "8084"
        self.client_script = os.path.join(os.path.dirname(__file__), '../../vpn-sentinel-client/vpn-sentinel-client.py')
        self.health_monitor_script = os.path.join(os.path.dirname(__file__), '../../vpn_sentinel_common/health_scripts/health_monitor_wrapper.py')

        if not ensure_scripts_exist(self.client_script, self.health_monitor_script):
            self.skipTest("Required scripts not found")

    def tearDown(self):
        if self.client_process:
            stop_client_process(self.client_process)
        # Ensure no stray health-monitor processes remain from tests
        kill_health_monitor_processes()

    # use shared probe_url from helpers

    def test_monitor_started_by_default(self):
        """Client should start monitor by default when VPN_SENTINEL_HEALTH_MONITOR is unset"""
        env = os.environ.copy()
        # Do NOT set VPN_SENTINEL_HEALTH_MONITOR or VPN_SENTINEL_HEALTH_PORT
        # The monitor should bind to the default port 8082
        env.update({
            'VPN_SENTINEL_URL': 'http://localhost:5000',
            'VPN_SENTINEL_API_PATH': '/api/v1',
            'VPN_SENTINEL_CLIENT_ID': 'test-default-monitor',
        })

        # Start the client and monitor using shared helper
        default_port = '8082'
        self.client_process = start_client_with_monitor(
            self.client_script,
            default_port,
            client_id='test-default-monitor',
            extra_env=env,
            wait=4,
        )

        # Ensure client process is running
        self.assertIsNone(self.client_process.poll())

        # Verify health monitor process was started (search for health_monitor or health-monitor process)
        result = subprocess.run(['pgrep', '-u', str(os.getuid()), '-f', 'health_monitor'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, msg=f"health_monitor process not found; stdout={result.stdout}, stderr={result.stderr}")

        # Check that the default health port (8082) is being used
        default_port = '8082'
        health_url = f"http://localhost:{default_port}/client/health"
        try:
            resp = probe_url(health_url, timeout=3)
            # If we received a response, the monitor is listening on the default port
            self.assertIn(resp.status_code, (200, 503))
        except requests.exceptions.RequestException as e:
            self.fail(f"Expected health endpoint at default port {default_port} to be reachable: {e}")

    def test_health_endpoint_unavailable_when_disabled(self):
        """Health endpoint should be unreachable when monitor is explicitly disabled"""
        env = os.environ.copy()
        env.update({
            'VPN_SENTINEL_HEALTH_MONITOR': 'false',
            'VPN_SENTINEL_HEALTH_PORT': self.test_port,
            'VPN_SENTINEL_URL': 'http://localhost:5000',
            'VPN_SENTINEL_API_PATH': '/api/v1',
            'VPN_SENTINEL_CLIENT_ID': 'test-disabled-monitor',
        })

        # Start client with monitor disabled
        self.client_process = start_client_with_monitor(
            self.client_script,
            self.test_port,
            client_id='test-disabled-monitor',
            extra_env=env,
            wait=3,
        )

        # Client should be running
        self.assertIsNone(self.client_process.poll())

        health_url = f"http://localhost:{self.test_port}/client/health"
        try:
            resp = requests.get(health_url, timeout=2)
            # If we received a response, it's unexpected
            self.fail(f"Expected connection failure but got HTTP {resp.status_code}")
        except requests.exceptions.RequestException:
            # Expected: connection refused / timeout / no endpoint
            pass


    def test_monitor_uses_custom_port(self):
        """When VPN_SENTINEL_HEALTH_PORT is set, the monitor should bind to that port and not the default."""
        env = os.environ.copy()
        env.update({
            'VPN_SENTINEL_HEALTH_PORT': self.test_port,
            'VPN_SENTINEL_URL': 'http://localhost:5000',
            'VPN_SENTINEL_API_PATH': '/api/v1',
            'VPN_SENTINEL_CLIENT_ID': 'test-custom-port',
        })

        self.client_process = start_client_with_monitor(
            self.client_script,
            self.test_port,
            client_id='test-custom-port',
            extra_env=env,
            wait=4,
        )

        # Client should be running
        self.assertIsNone(self.client_process.poll())

        # Custom port should respond
        health_url_custom = f"http://localhost:{self.test_port}/client/health"
        try:
            resp = probe_url(health_url_custom, timeout=3)
            self.assertIn(resp.status_code, (200, 503))
        except requests.exceptions.RequestException as e:
            self.fail(f"Expected health endpoint at custom port {self.test_port} to be reachable: {e}")

        # Default port should NOT be responding when custom port is set
        default_port = '8082'
        health_url_default = f"http://localhost:{default_port}/client/health"
        try:
            # Use fewer retries here; we expect no listener on default port when custom port is set
            resp2 = probe_url(health_url_default, timeout=2, retries=2, backoff_factor=0.2)
            # If default port responds, that's unexpected
            self.fail(f"Expected default port {default_port} to be unused, but got HTTP {resp2.status_code}")
        except requests.exceptions.RequestException:
            # Expected: connection refused / timeout / no endpoint
            pass


if __name__ == '__main__':
    unittest.main()
