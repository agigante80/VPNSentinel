import os
import time
import json
import subprocess
import tempfile
import unittest

from tests.helpers import start_client_with_monitor, stop_client_process, kill_health_monitor_processes, ensure_scripts_exist


import os
import time
import json
import tempfile
import unittest

from tests.helpers import start_client_with_monitor, stop_client_process, kill_health_monitor_processes, ensure_scripts_exist


class TestClientKeepaliveClientID(unittest.TestCase):
    """Integration tests for keepalive client_id behavior.

    These tests use the VPN_SENTINEL_TEST_CAPTURE_PATH hook so they do not require an HTTP server.
    """

    def setUp(self):
        self.client_process = None
        self.client_script = os.path.join(os.path.dirname(__file__), '../../vpn-sentinel-client/vpn-sentinel-client.py')
        self.health_monitor_script = os.path.join(os.path.dirname(__file__), '../../vpn_sentinel_common/health_scripts/health-monitor.sh')

        if not ensure_scripts_exist(self.client_script, self.health_monitor_script):
            self.skipTest('Required scripts not found')

        # Use a deterministic capture file inside the tests directory to avoid /tmp races
        self.capture_path = os.path.join(os.path.dirname(__file__), 'tmp_keepalive_capture.json')
        # ensure file does not exist
        try:
            os.unlink(self.capture_path)
        except Exception:
            pass
        # short interval so keepalive posts quickly
        self.interval = '1'

    def tearDown(self):
        if self.client_process:
            stop_client_process(self.client_process)
        kill_health_monitor_processes()
        try:
            os.unlink(self.capture_path)
        except Exception:
            pass

    def _read_captured_payloads(self):
        if not os.path.exists(self.capture_path):
            return []
        with open(self.capture_path, 'rb') as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        parsed = []
        for b in lines:
            try:
                parsed.append(json.loads(b.decode('utf-8')))
            except Exception:
                pass
        return parsed

    def test_client_id_generated_when_unset(self):
        # Do not set VPN_SENTINEL_CLIENT_ID so the client generates one
        env = os.environ.copy()
        env.update({
            'VPN_SENTINEL_API_PATH': '/api/v1',
            'VPN_SENTINEL_INTERVAL': self.interval,
            'VPN_SENTINEL_TIMEOUT': '2',
            'VPN_SENTINEL_TEST_CAPTURE_PATH': self.capture_path,
        })

        self.client_process = start_client_with_monitor(self.client_script, '0', client_id='', extra_env=env, wait=4)

        # wait for at least one keepalive to be emitted
        payloads = []
        for _ in range(20):
            payloads = self._read_captured_payloads()
            if payloads:
                break
            time.sleep(0.5)

        self.assertTrue(len(payloads) >= 1, 'No keepalive payloads captured')
        first = payloads[0]
        self.assertIn('client_id', first)
        self.assertTrue(isinstance(first['client_id'], str) and len(first['client_id']) > 0)

    def test_client_id_sent_when_set(self):
        explicit_id = 'my-office-vpn'
        env = os.environ.copy()
        env.update({
            'VPN_SENTINEL_API_PATH': '/api/v1',
            'VPN_SENTINEL_CLIENT_ID': explicit_id,
            'VPN_SENTINEL_INTERVAL': self.interval,
            'VPN_SENTINEL_TIMEOUT': '2',
            'VPN_SENTINEL_TEST_CAPTURE_PATH': self.capture_path,
        })

        self.client_process = start_client_with_monitor(self.client_script, '0', client_id=explicit_id, extra_env=env, wait=4)

        payloads = []
        for _ in range(20):
            payloads = self._read_captured_payloads()
            if payloads:
                break
            time.sleep(0.5)

        self.assertTrue(len(payloads) >= 1, 'No keepalive payloads captured')
        first = payloads[0]
        self.assertIn('client_id', first)
        self.assertEqual(first['client_id'], explicit_id)


if __name__ == '__main__':
    unittest.main()
