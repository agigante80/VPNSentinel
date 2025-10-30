#!/usr/bin/env python3
"""vpn-sentinel-server health monitor

This is a tiny, testable health-monitor process that runs until terminated.
It logs a heartbeat periodically and supports clean shutdown on SIGTERM/SIGINT.

Configuration is via environment variables:
- VPN_SENTINEL_MONITOR_INTERVAL (seconds, default 10)
- VERSION (optional)
- COMMIT_HASH (optional)

The script intentionally has no external dependencies so it can run in CI
and minimal containers.
"""
from __future__ import annotations

import logging
import os
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

# When this script is executed directly in tests, the repository root may not be
# on sys.path. Ensure the repo root is first so relative imports like
# `vpn_sentinel_common` work without installing the package.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


from vpn_sentinel_common.logging import log_info, log_warn, log_error


SHUTDOWN = threading.Event()


def handle_signal(signum, frame):
    log_info("monitor", f"Received signal {signum}; shutting down gracefully")
    SHUTDOWN.set()


def monitor_loop(interval: int, component: str = "monitor") -> None:
    version = os.getenv("VERSION", "unknown")
    commit = os.getenv("COMMIT_HASH", "unknown")
    log_info(component, f"Starting health monitor | VERSION={version} COMMIT={commit}")
    next_ts = time.time()
    try:
        while not SHUTDOWN.is_set():
            now = datetime.utcnow().isoformat() + "Z"
            log_info(component, f"heartbeat | time={now}")
            # Sleep in small increments so we can react to signals quickly
            slept = 0.0
            while slept < interval and not SHUTDOWN.is_set():
                time.sleep(0.2)
                slept += 0.2
            next_ts += interval
    except Exception as exc:  # pragma: no cover - defensive
        log_error(component, f"Unhandled exception in monitor loop: {exc}")
    finally:
        log_info(component, "Monitor stopped")


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    # Basic logging configuration (stdout, human-friendly)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    interval = int(os.getenv("VPN_SENTINEL_MONITOR_INTERVAL", "10"))

    # Install termination handlers
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    monitor_loop(interval, component="monitor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
