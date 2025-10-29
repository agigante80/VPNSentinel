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


SHUTDOWN = threading.Event()


def log_info(component: str, msg: str) -> None:
    logging.info(f"{component} | {msg}")


def log_warn(component: str, msg: str) -> None:
    logging.warning(f"{component} | {msg}")


def log_error(component: str, msg: str) -> None:
    logging.error(f"{component} | {msg}")


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
