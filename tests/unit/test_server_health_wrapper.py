import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT.parent / 'vpn-sentinel-server' / 'health-monitor-wrapper.sh'
PYTHON = sys.executable or 'python3'
DUMMY = ROOT / 'fixtures' / 'dummy_server.py'


def test_wrapper_start_stop_creates_and_removes_pidfile(tmp_path):
    pidfile = tmp_path / 'server-health.pid'
    # build command to run wrapper start
    env = os.environ.copy()
    env['VPN_SENTINEL_SERVER_HEALTH_PIDFILE'] = str(pidfile)
    # point wrapper to the dummy server via env var
    env['VPN_SENTINEL_SERVER_DUMMY_CMD'] = f"{PYTHON} {DUMMY} 9999"

    # start wrapper in background
    p = subprocess.Popen(['bash', str(WRAPPER)], env=env)

    # wait for pidfile to appear
    timeout = time.time() + 5
    while time.time() < timeout:
        if pidfile.exists():
            break
        time.sleep(0.1)
    assert pidfile.exists(), 'pidfile was not created'

    # read pid and check process exists
    pid = int(pidfile.read_text().strip())
    try:
        os.kill(pid, 0)
    except OSError:
        raise AssertionError('process from pidfile is not running')

    # now stop via wrapper --stop
    stop = subprocess.run(['bash', str(WRAPPER), '--stop'], env=env)
    assert stop.returncode == 0

    # wait for pidfile to be removed
    timeout = time.time() + 5
    while time.time() < timeout:
        if not pidfile.exists():
            break
        time.sleep(0.1)
    assert not pidfile.exists(), 'pidfile was not removed after stop'

    # ensure background wrapper process has exited
    p.poll()
    if p.returncode is None:
        # try terminate
        p.terminate()
        p.wait(timeout=2)
