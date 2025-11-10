import os
import time
import unittest
from tests.helpers import (
    start_client_with_monitor,
    stop_client_process,
    read_server_url_from_proc,
    ensure_scripts_exist,
)


class TestApiPath(unittest.TestCase):
    def setUp(self):
        self.client_script = os.path.join(os.path.dirname(__file__), '../../vpn-sentinel-client/vpn-sentinel-client.py')
        self.health_monitor_script = os.path.join(os.path.dirname(__file__), '../../vpn_sentinel_common/health_scripts/health-monitor.sh')
        if not ensure_scripts_exist(self.client_script, self.health_monitor_script):
            self.skipTest('Required scripts not found')
        self.proc = None

    def tearDown(self):
        if self.proc:
            stop_client_process(self.proc)

    def test_api_path_default(self):
        # Start the client without setting VPN_SENTINEL_API_PATH
        self.proc = start_client_with_monitor(self.client_script, 8090, client_id='test-api-default', extra_env={'VPN_SENTINEL_URL': 'http://localhost:5000'})
        server_url = read_server_url_from_proc(self.proc, timeout=3)
        self.assertTrue(server_url.endswith('/api/v1'), f'Expected default /api/v1, got {server_url}')

    def test_api_path_with_leading_slash(self):
        self.proc = start_client_with_monitor(self.client_script, 8091, client_id='test-api-slash', extra_env={'VPN_SENTINEL_URL': 'http://localhost:5000', 'VPN_SENTINEL_API_PATH': '/test/v2'})
        server_url = read_server_url_from_proc(self.proc, timeout=3)
        self.assertTrue(server_url.endswith('/test/v2'), f'Expected /test/v2, got {server_url}')

    def test_api_path_without_leading_slash(self):
        self.proc = start_client_with_monitor(self.client_script, 8092, client_id='test-api-noslash', extra_env={'VPN_SENTINEL_URL': 'http://localhost:5000', 'VPN_SENTINEL_API_PATH': 'other/v3'})
        server_url = read_server_url_from_proc(self.proc, timeout=3)
        self.assertTrue(server_url.endswith('/other/v3'), f'Expected /other/v3 (with leading slash added), got {server_url}')


if __name__ == '__main__':
    unittest.main()
