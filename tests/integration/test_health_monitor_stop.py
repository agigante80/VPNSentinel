import os
import time
import subprocess


def test_health_monitor_stop_removes_pidfile_and_stops_process(tmp_path):
    # Use a predictable pidfile path in tmp
    pidfile = tmp_path / "vpn-sentinel-health-monitor.pid"
    pidfile_path = str(pidfile)

    # Start a benign background process whose argv contains 'health-monitor'
    # so the stop helper recognizes it as a monitor-like process.
    # Use bash -c 'exec -a health-monitor /bin/sleep 60' to set argv[0].
    p = subprocess.Popen(["bash", "-c", "exec -a health-monitor /bin/sleep 60"])
    try:
        # Write its pid into the pidfile to simulate a running monitor
        pidfile.write_text(str(p.pid))

        env = os.environ.copy()
        env["VPN_SENTINEL_HEALTH_PIDFILE"] = pidfile_path

        # Invoke the script with --stop
        script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "vpn-sentinel-client", "health-monitor.sh")
        script = os.path.abspath(script)
        rc = subprocess.call([script, "--stop"], env=env)

        # Ensure script exited successfully
        assert rc == 0

        # Give process a moment to die
        time.sleep(0.5)

        # Process should be gone
        ret = p.poll()
        assert ret is not None

        # Pidfile should be removed
        assert not pidfile.exists()
    finally:
        try:
            p.kill()
        except Exception:
            pass
