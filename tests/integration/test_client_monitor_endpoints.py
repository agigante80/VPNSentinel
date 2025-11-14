import os
import time
import subprocess
import signal
import requests
from tests.helpers import probe_url, start_client_with_monitor, stop_client_process, kill_health_monitor_processes, ensure_scripts_exist, assert_health_schema
import unittest


class TestClientMonitorEndpoints(unittest.TestCase):
    """Integration tests for individual health-monitor endpoints

    Tests:
    - GET /client/health -> returns JSON and status 200 or 503
    - GET /client/health/ready -> returns HTTP status indicating readiness (200 or 503)
    - GET /client/health/startup -> returns a small JSON or text indicating monitor running
    """

    def setUp(self):
        self.client_process = None
        self.test_port = '8085'
        self.client_script = os.path.join(os.path.dirname(__file__), '../../vpn-sentinel-client/vpn-sentinel-client.py')
        self.health_monitor_script = os.path.join(os.path.dirname(__file__), '../../vpn_sentinel_common/health_scripts/health_monitor_wrapper.py')

        if not ensure_scripts_exist(self.client_script, self.health_monitor_script):
            self.skipTest('Required scripts not found')

    def tearDown(self):
        if self.client_process:
            stop_client_process(self.client_process)
        kill_health_monitor_processes()

    def start_client_with_monitor(self, port):
        # Use shared helper
        self.client_process = start_client_with_monitor(self.client_script, port, client_id='test-endpoints', wait=1)

    # use probe_url from tests.helpers

    def test_health_full_endpoint(self):
        self.start_client_with_monitor(self.test_port)
        health_url = f'http://localhost:{self.test_port}/client/health'
        resp = probe_url(health_url, timeout=5)
        self.assertIn(resp.status_code, (200, 503))
        # Expect JSON body with 'status' and 'checks'
        try:
            data = resp.json()
            self.assertIn('status', data)
            self.assertIn('checks', data)
        except ValueError:
            self.fail('Expected JSON response from /client/health')

    def test_health_ready_endpoint(self):
        self.start_client_with_monitor(self.test_port)
        ready_url = f'http://localhost:{self.test_port}/client/health/ready'
        resp = probe_url(ready_url, timeout=5)
        # ready may be 200 or 503 depending on environment
        self.assertIn(resp.status_code, (200, 503))

    def test_health_startup_endpoint(self):
        self.start_client_with_monitor(self.test_port)
        startup_url = f'http://localhost:{self.test_port}/client/health/startup'
        resp = probe_url(startup_url, timeout=5)
        # Accept 200 and small JSON or text
        self.assertEqual(resp.status_code, 200)
        # If JSON, check for some key or accept plain text
        try:
            data = resp.json()
            # either contains a 'status' key or 'message'
            self.assertTrue('status' in data or 'message' in data)
        except ValueError:
            # allow plain text response
            self.assertTrue(len(resp.text) > 0)


if __name__ == '__main__':
    unittest.main()
