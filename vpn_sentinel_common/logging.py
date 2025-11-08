"""Small logging helpers used across the project.

Keep this intentionally tiny and dependency-free so tests and CI can import it
without adding runtime dependencies.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
import zoneinfo
import os


def _configure_once():
    # Basic config: stream to stdout with human-friendly format.
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
            handlers=[logging.StreamHandler(sys.stdout)],
        )


def get_current_time():
    """Get current time in configured timezone.

    Returns a timezone-aware datetime similar to the legacy implementation.
    """
    tz = zoneinfo.ZoneInfo(os.getenv('TZ', 'UTC'))
    return datetime.now(tz)


def log_message(level: str, component: str, message: str) -> None:
    """Log a message with structured format: timestamp level [component] message."""
    timestamp = datetime.now(zoneinfo.ZoneInfo("UTC")).strftime('%Y-%m-%dT%H:%M:%SZ')
    print(f"{timestamp} {level} [{component}] {message}", flush=True)


def log_info(component: str, msg: str) -> None:
    _configure_once()
    # Also print to stdout to preserve legacy behaviour used by tests
    print(f"INFO [{component}] {msg}", flush=True)
    logging.info(f"{component} | {msg}")


def log_error(component: str, msg: str) -> None:
    _configure_once()
    # Also print to stdout to preserve legacy behaviour used by tests
    print(f"ERROR [{component}] {msg}", flush=True)
    logging.error(f"{component} | {msg}")


def log_warn(component: str, msg: str) -> None:
    _configure_once()
    # Also print to stdout to preserve legacy behaviour used by tests
    print(f"WARN [{component}] {msg}", flush=True)
    logging.warning(f"{component} | {msg}")
