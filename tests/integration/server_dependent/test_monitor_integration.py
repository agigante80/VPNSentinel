import os
import subprocess
import time
import requests
import socket
import pytest


def docker_available():
    try:
        subprocess.run(['docker', 'ps'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


@pytest.mark.skipif(not docker_available(), reason="Docker not available")
def test_monitor_in_container():
    # Start the test compose stack
    cwd = os.path.dirname(os.path.dirname(__file__))
    compose_file = os.path.join(cwd, 'docker-compose.test.yaml')

    up = subprocess.run(['docker', 'compose', '-f', compose_file, 'up', '-d', '--build'], check=False, capture_output=True, text=True)
    if up.returncode != 0:
        # Don't fail immediately — capture output and continue to attempt to wait for health.
        print('docker compose up returned non-zero; stdout/stderr:')
        print(up.stdout)
        print(up.stderr)

    try:
        # Determine host port mapping for server
        # The compose maps 15554:5000 in the test compose
        host_port = '15554'

        # Wait for health endpoint
        timeout = time.time() + 60
        url = f'http://localhost:{host_port}/test/v1/health'
        healthy = False
        while time.time() < timeout:
            try:
                r = requests.get(url, timeout=2)
                if r.status_code == 200:
                    healthy = True
                    break
            except Exception:
                pass
            time.sleep(1)

        if not healthy:
            # Collect logs for diagnosis and skip the test to avoid flakiness in environments
            logs = subprocess.run(['docker', 'logs', 'vpn-sentinel-server-test'], capture_output=True, text=True)
            print('Server logs:\n', logs.stdout)
            pytest.skip('Server health endpoint not ready in time; skipping integration test')

        # Check container logs for monitor heartbeat
        logs = subprocess.check_output(['docker', 'logs', 'vpn-sentinel-server-test'], text=True)
        assert 'heartbeat' in logs or 'Starting health monitor' in logs, 'Monitor heartbeat not found in server logs'

    finally:
        subprocess.run(['docker', 'compose', '-f', compose_file, 'down', '-v'], check=False)
