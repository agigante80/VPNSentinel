import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MONITOR = ROOT / 'vpn_sentinel_common' / 'health_monitor.py'
PYTHON = sys.executable or 'python3'


def read_lines_until(proc, predicate, timeout=5.0):
    """Read lines from proc.stdout until predicate(line) is True or timeout."""
    end = time.time() + timeout
    buf = []
    while time.time() < end:
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.05)
            continue
        buf.append(line)
        if predicate(line):
            return buf
    return buf


def test_monitor_heartbeats_and_shutdown(tmp_path):
    assert MONITOR.exists(), f"{MONITOR} not found"

    env = os.environ.copy()
    # Use a short interval so the test runs quickly
    env['VPN_SENTINEL_MONITOR_INTERVAL'] = '1'
    env['PYTHONUNBUFFERED'] = '1'
    env['VERSION'] = 'test-ver'
    env['COMMIT_HASH'] = 'deadbeef'
    env['PYTHONPATH'] = str(ROOT)

    proc = subprocess.Popen([PYTHON, str(MONITOR)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, text=True)

    try:
        # Wait for the startup line
        lines = read_lines_until(proc, lambda l: 'Starting health monitor' in l, timeout=3.0)
        assert any('Starting health monitor' in l for l in lines), f"startup line not seen in output: {lines}"

        # Wait for at least one heartbeat
        lines = read_lines_until(proc, lambda l: 'heartbeat' in l, timeout=5.0)
        assert any('heartbeat' in l for l in lines), f"no heartbeat seen in output: {lines}"

        # Send SIGTERM to request graceful shutdown
        proc.send_signal(signal.SIGTERM)

        # Give the signal handler a moment to run
        time.sleep(0.1)

        # Wait for shutdown messages
        shutdown_lines = read_lines_until(proc, lambda l: 'Monitor stopped' in l or 'shutting down gracefully' in l, timeout=5.0)
        assert any('Monitor stopped' in l or 'shutting down gracefully' in l for l in shutdown_lines), f"no shutdown confirmation in output: {shutdown_lines}"

        # Wait for process to exit
        proc.wait(timeout=5.0)
        assert proc.returncode == 0 or proc.returncode == None or proc.returncode == 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=2)
