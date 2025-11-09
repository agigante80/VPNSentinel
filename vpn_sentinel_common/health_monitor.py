#!/usr/bin/env python3
"""Standalone health

This script runs a monitor that emits heartbeats and handles graceful shutdown.
"""
import os
import signal
import sys
import time
from pathlib import Path

# Add the parent directory to sys.path so we can import vpn_sentinel_common
sys.path.insert(0, str(Path(__file__).parent.parent))

from vpn_sentinel_common.monitor import Monitor
from vpn_sentinel_common.log_utils import log_info


def heartbeat_callback(heartbeat):
    """Callback for monitor heartbeats."""
    log_info("monitor", f"heartbeat: {heartbeat}")


def main():
    """Main entry point for the health monitor."""
    # Get configuration from environment
    interval = float(os.getenv('VPN_SENTINEL_MONITOR_INTERVAL', '30'))
    version = os.getenv('VERSION', 'unknown')
    commit_hash = os.getenv('COMMIT_HASH', 'unknown')

    log_info("monitor", f"Starting health monitor (version: {version}, commit: {commit_hash})")

    # Create and start the monitor
    monitor = Monitor(
        component="health-monitor",
        interval=interval,
        on_heartbeat=heartbeat_callback
    )

    # Handle SIGTERM for graceful shutdown
    stop_requested = False
    def signal_handler(signum, frame):
        nonlocal stop_requested
        log_info("monitor", "Received SIGTERM, shutting down gracefully...")
        monitor.stop()
        stop_requested = True

    signal.signal(signal.SIGTERM, signal_handler)

    try:
        monitor.start()
        # Keep the main thread alive until stop requested
        while not stop_requested:
            time.sleep(0.1)
    except KeyboardInterrupt:
        log_info("monitor", "Interrupted, shutting down...")
        monitor.stop()
    finally:
        monitor.stop()  # Ensure monitor is stopped
        log_info("monitor", "Monitor stopped")


if __name__ == "__main__":
    main()