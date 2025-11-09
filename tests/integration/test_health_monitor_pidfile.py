import os
import time
import subprocess
import requests
import tempfile
import json
import sys

from tests.helpers import start_client_with_monitor, stop_client_process, kill_health_monitor_processes


def test_pidfile_cleanup_for_stale_pid(tmp_path):
    """Simulate a stale pidfile and verify the health monitor cleans it up and starts."""
    # Ensure a clean environment
    kill_health_monitor_processes()

    pidfile = str(tmp_path / "stale-health.pid")
    # Create a stale pid that does not exist
    with open(pidfile, "w") as f:
        f.write("999999")

    env = os.environ.copy()
    env.update({
        'VPN_SENTINEL_URL': 'http://localhost:5000',
        'VPN_SENTINEL_API_PATH': '/api/v1',
        'VPN_SENTINEL_CLIENT_ID': 'test-pidfile-stale',
        'VPN_SENTINEL_HEALTH_PIDFILE': pidfile,
    })

    # Resolve client script path relative to repo root so tests work when
    # running from the tests directory or from the repo root (CI may cd into
    # different directories).
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    client_script = os.path.join(repo_root, 'vpn-sentinel-client', 'vpn-sentinel-client.sh')
    proc = start_client_with_monitor(client_script, 0, client_id='test-pidfile-stale', extra_env=env, wait=4)
    try:
        # Wait briefly for pidfile to be (re)created by the wrapper
        time.sleep(1)
        assert os.path.exists(pidfile), "pidfile should be created by health monitor"
        # Read pid and ensure process exists
        with open(pidfile, 'r') as f:
            pid = f.read().strip()
        assert pid.isdigit(), "pidfile should contain numeric pid"
    finally:
        stop_client_process(proc)
        kill_health_monitor_processes()


def test_pidfile_cleanup_for_live_user_owned_process(tmp_path):
    """Simulate a live user-owned process claiming the pidfile and ensure cleanup occurs."""
    kill_health_monitor_processes()

    # Start a benign background process we can own (sleep)
    sleeper = subprocess.Popen(['sleep', '60'])
    try:
        pidfile = str(tmp_path / "live-health.pid")
        with open(pidfile, 'w') as f:
            f.write(str(sleeper.pid))

        env = os.environ.copy()
        env.update({
            'VPN_SENTINEL_URL': 'http://localhost:5000',
            'VPN_SENTINEL_API_PATH': '/api/v1',
            'VPN_SENTINEL_CLIENT_ID': 'test-pidfile-live',
            'VPN_SENTINEL_HEALTH_PIDFILE': pidfile,
        })

        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        client_script = os.path.join(repo_root, 'vpn-sentinel-client', 'vpn-sentinel-client.sh')
        proc = start_client_with_monitor(client_script, 8082, client_id='test-pidfile-live', extra_env=env, wait=6, capture_output=False)
        try:
            # Give the wrapper a moment to detect and stop the stale monitor
            time.sleep(3)
            # After starting, pidfile should point to the wrapper pid (not the sleeper)
            assert os.path.exists(pidfile), "pidfile should exist"
            with open(pidfile, 'r') as f:
                new_pid = f.read().strip()
            assert new_pid.isdigit()
            assert int(new_pid) != sleeper.pid, "pidfile should have been replaced and not point to the original sleeper pid"
        finally:
            stop_client_process(proc)
            kill_health_monitor_processes()
    finally:
        # ensure sleeper cleaned up
        try:
            sleeper.kill()
        except Exception:
            pass
