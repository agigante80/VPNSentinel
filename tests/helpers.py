import time
import requests
import subprocess
import os
import signal
import sys


def probe_url(url, timeout=5, retries=5, backoff_factor=0.5):
    """Probe a URL with retries and exponential backoff.

    Returns the requests.Response on success or raises the last exception on failure.
    """
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, timeout=timeout)
            return resp
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            sleep_time = backoff_factor * (2 ** (attempt - 1))
            time.sleep(sleep_time)
    # all attempts failed
    raise last_exc


def kill_health_monitor_processes():
    """Attempt to kill any running health-monitor.sh processes (best-effort)."""
    try:
        subprocess.run(['pkill', '-f', 'health-monitor.sh'], capture_output=True)
    except Exception:
        pass


def start_client_with_monitor(client_script, port, client_id='test-helper', extra_env=None, wait=4):
    """Start the vpn-sentinel-client script with a health monitor on the specified port.

    Returns the subprocess.Popen object.
    """
    env = os.environ.copy()
    # Do not overwrite PATH here - preserve the test runner's environment so
    # subprocesses (notably the health monitor's Python detection) can find
    # executables installed in CI/toolcache locations.
    env.update({
        'VPN_SENTINEL_HEALTH_PORT': str(port),
        'VPN_SENTINEL_URL': 'http://localhost:5000',
        'VPN_SENTINEL_API_PATH': '/api/v1',
    })
    # Short timeout for tests to avoid long external HTTP waits
    env.setdefault('VPN_SENTINEL_TIMEOUT', '2')
    # Only set VPN_SENTINEL_CLIENT_ID when a non-empty client_id is provided
    if client_id:
        env['VPN_SENTINEL_CLIENT_ID'] = client_id
    if extra_env:
        env.update(extra_env)

    # extra_env may include test-only vars (like VPN_SENTINEL_TEST_CAPTURE_PATH)

    # Ensure no pre-existing health-monitor processes
    kill_health_monitor_processes()
    time.sleep(0.5)

    proc = subprocess.Popen(
        [client_script],
        env=env,
        preexec_fn=os.setsid,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    # allow monitor to start (tests use probe helper for endpoint readiness)
    time.sleep(wait)
    return proc


def stop_client_process(proc, timeout=5):
    """Terminate the process group for proc and wait, with fallback to SIGKILL."""
    if not proc:
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=timeout)
    except Exception:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            pass


def ensure_scripts_exist(client_script, health_monitor_script):
    return os.path.exists(client_script) and os.path.exists(health_monitor_script)


def assert_health_schema(data):
    """Basic assertion helper for the /client/health JSON schema.

    Checks that top-level keys exist and have expected types. Raises AssertionError if invalid.
    """
    assert isinstance(data, dict), "health response must be a JSON object"
    # status
    assert 'status' in data, "missing 'status'"
    assert data['status'] in ('healthy', 'degraded', 'unhealthy'), "invalid 'status' value"
    # timestamp
    assert 'timestamp' in data, "missing 'timestamp'"
    # checks
    assert 'checks' in data and isinstance(data['checks'], dict), "missing or invalid 'checks'"
    # system
    assert 'system' in data and isinstance(data['system'], dict), "missing or invalid 'system'"
    # issues (optional)
    if 'issues' in data:
        assert isinstance(data['issues'], list), "'issues' must be a list"


def read_server_url_from_proc(proc, timeout=5):
    """Read stdout lines from proc until a line containing 'Server:' is found, return the URL portion.

    Returns the server URL string or raises RuntimeError on timeout.
    """
    if not proc or proc.stdout is None:
        raise RuntimeError("Process has no stdout to read from")
    end = time.time() + timeout
    while time.time() < end:
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.1)
            continue
        if 'Server:' in line:
            # expected format: [TIMESTAMP] LEVEL [config] Server: http://.../api
            parts = line.split('Server:', 1)
            if len(parts) > 1:
                return parts[1].strip()
    raise RuntimeError('Timed out waiting for Server: line in process stdout')
