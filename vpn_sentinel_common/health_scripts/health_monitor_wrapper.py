#!/usr/bin/env python3
"""VPN Sentinel Health Monitor Wrapper.

This wrapper manages the health monitor process and handles PID file management.
"""
import os
import sys
import signal
import subprocess
import time
from pathlib import Path

# Add the parent directory to sys.path so we can import vpn_sentinel_common
sys.path.insert(0, str(Path(__file__).parent.parent))

# Health monitor main function will be called via subprocess


def get_pidfile():
    """Get the PID file path."""
    return os.getenv('VPN_SENTINEL_HEALTH_PIDFILE', '/tmp/vpn-sentinel-health-monitor.pid')


def read_pidfile():
    """Read PID from pidfile."""
    pidfile = get_pidfile()
    try:
        with open(pidfile, 'r') as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None


def write_pidfile(pid):
    """Write PID to pidfile."""
    pidfile = get_pidfile()
    with open(pidfile, 'w') as f:
        f.write(str(pid))


def remove_pidfile():
    """Remove the PID file."""
    pidfile = get_pidfile()
    try:
        os.remove(pidfile)
    except FileNotFoundError:
        pass


def stop_monitor():
    """Stop the running health monitor."""
    pid = read_pidfile()
    if pid is None:
        print("No PID file found", file=sys.stderr)
        return 0

    try:
        # Check if process exists and is owned by current user
        current_uid = os.getuid()
        proc_uid = subprocess.run(
            ['ps', '-o', 'uid=', '-p', str(pid)],
            capture_output=True,
            text=True,
            timeout=5
        ).stdout.strip()

        if proc_uid and int(proc_uid) == current_uid:
            # Send TERM signal
            os.kill(pid, signal.SIGTERM)

            # Wait a bit for graceful shutdown
            time.sleep(1)

            # Check if still running
            try:
                os.kill(pid, 0)  # Signal 0 just checks if process exists
                # If still running, force kill
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass  # Process already exited

            remove_pidfile()
            print("Health monitor stopped")
            return 0
        else:
            print(f"Refusing to stop pid {pid}: not owned by current user", file=sys.stderr)
            return 3
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, ValueError):
        # Process doesn't exist or other error
        remove_pidfile()
        return 0


def cleanup_stale_pidfile():
    """Clean up stale PID file if it exists.

    This function is more aggressive than the previous version:
    - Checks if PID file exists
    - If PID in file corresponds to a running process owned by current user, terminates it
    - Always removes the PID file to ensure clean state
    """
    pidfile = get_pidfile()
    if os.path.exists(pidfile):
        # Read the PID from file
        existing_pid = read_pidfile()
        if existing_pid is not None:
            try:
                # Check if process exists and is owned by current user
                current_uid = os.getuid()
                proc_uid = subprocess.run(
                    ['ps', '-o', 'uid=', '-p', str(existing_pid)],
                    capture_output=True,
                    text=True,
                    timeout=2
                ).stdout.strip()

                if proc_uid and int(proc_uid) == current_uid:
                    print(f"Found live process {existing_pid} in PID file, terminating...", file=sys.stderr)
                    try:
                        # Send TERM signal first
                        os.kill(existing_pid, signal.SIGTERM)
                        # Wait a bit for graceful shutdown
                        time.sleep(0.5)
                        # Check if still running
                        os.kill(existing_pid, 0)
                        # If still running, force kill
                        os.kill(existing_pid, signal.SIGKILL)
                        time.sleep(0.1)
                    except ProcessLookupError:
                        pass  # Process already exited
                    print(f"Terminated stale health monitor process {existing_pid}", file=sys.stderr)
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, ValueError, OSError) as e:
                # Process doesn't exist or other error - this is fine
                pass

        # Always remove the PID file to ensure clean state
        try:
            os.remove(pidfile)
            print(f"Removed stale PID file: {pidfile}", file=sys.stderr)
        except OSError as e:
            pass
    else:
        print(f"DEBUG: PID file does not exist: {pidfile}", file=sys.stderr)


def start_monitor():
    """Start the health monitor."""
    # Clean up any stale PID file first
    cleanup_stale_pidfile()

    # Write our PID to file
    write_pidfile(os.getpid())

    try:
        # Run the health monitor as a subprocess
        import subprocess
        import sys

        # Use the venv python if available, otherwise system python
        venv_python = "/opt/venv/bin/python3"
        python_exe = venv_python if os.path.exists(venv_python) else sys.executable

        # Run the health monitor as a subprocess so we can manage its lifecycle
        health_monitor_path = Path(__file__).parent / 'health_monitor.py'
        cmd = [python_exe, str(health_monitor_path)]
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path(__file__).parent.parent)

        process = subprocess.Popen(cmd, env=env)
        process.wait()
    finally:
        # Clean up PID file on exit
        remove_pidfile()


def show_help():
    """Show help message."""
    print("VPN Sentinel Health Monitor")
    print()
    print("Usage:")
    print("  health-monitor.py              Start the health monitor")
    print("  health-monitor.py --stop       Stop the running health monitor")
    print("  health-monitor.py --help|-h    Show this help")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        if sys.argv[1] in ('--help', '-h'):
            show_help()
            return 0
        elif sys.argv[1] == '--stop':
            return stop_monitor()
        else:
            print(f"Unknown option: {sys.argv[1]}", file=sys.stderr)
            return 2

    # No arguments - start the monitor
    start_monitor()
    return 0


if __name__ == '__main__':
    sys.exit(main())