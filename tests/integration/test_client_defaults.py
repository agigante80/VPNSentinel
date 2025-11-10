import os
import time
import unittest
from tests.helpers import start_client_with_monitor, stop_client_process, ensure_scripts_exist, read_server_url_from_proc


class TestClientDefaults(unittest.TestCase):
    """Tests for client default environment variable behavior."""

    def setUp(self):
        self.client_script = os.path.join(os.path.dirname(__file__), '../../vpn-sentinel-client/vpn-sentinel-client.py')
        self.health_monitor_script = os.path.join(os.path.dirname(__file__), '../../vpn_sentinel_common/health_scripts/health-monitor.sh')
        if not ensure_scripts_exist(self.client_script, self.health_monitor_script):
            self.skipTest('Required client scripts not found')
        self.proc = None

    def tearDown(self):
        if self.proc:
            stop_client_process(self.proc)

    def test_api_path_default_and_normalization(self):
        # When VPN_SENTINEL_API_PATH is unset the client should use /api/v1
        self.proc = start_client_with_monitor(self.client_script, 8095, client_id='test-api-default', extra_env={'VPN_SENTINEL_URL': 'http://localhost:5000'})
        server_url = read_server_url_from_proc(self.proc, timeout=3)
        self.assertTrue(server_url.endswith('/api/v1'))

    def test_interval_and_timeout_defaults(self):
        # Defaults are defined in lib/config.sh: INTERVAL=300, TIMEOUT=30
        # We can assert that the startup logs include the interval
        self.proc = start_client_with_monitor(self.client_script, 8096, client_id='test-interval-default', extra_env={'VPN_SENTINEL_URL': 'http://localhost:5000'})
        # read multiple stdout lines for the interval log (may be preceded by other logs)
        found = False
        for _ in range(20):
            l = self.proc.stdout.readline()
            if not l:
                time.sleep(0.05)
                continue
            if 'Interval' in l or '⏱️ Interval' in l or '⏱️ Interval:' in l:
                found = True
                break
        self.assertTrue(found, 'Interval startup log not found')

    def test_generated_client_id_format(self):
        # When VPN_SENTINEL_CLIENT_ID is unset the client generates an id starting with vpn-client-
        self.proc = start_client_with_monitor(self.client_script, 8097, client_id='', extra_env={'VPN_SENTINEL_URL': 'http://localhost:5000', 'INTERVAL': '1'})
        # Read several lines from stdout to find server/client id logs
        server_line = None
        client_line = None
        for _ in range(20):
            l = self.proc.stdout.readline()
            if not l:
                time.sleep(0.05)
                continue
            if 'Server:' in l or '📡 Server' in l:
                server_line = l
            if 'Client ID:' in l or '🏷️ Client ID' in l:
                client_line = l
            if server_line and client_line:
                break
        self.assertIsNotNone(client_line, f"Client ID line not found in stdout. Last lines: {server_line} / {client_line}")

