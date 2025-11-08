"""Deprecated logging shim that re-exports vpn_sentinel_common.logging
for backward compatibility during migration.
"""
import warnings

warnings.warn("vpn_sentinel_server.logging is deprecated; import from vpn_sentinel_common.logging instead", DeprecationWarning)

from vpn_sentinel_common.logging import get_current_time, log_info, log_warn, log_error  # noqa: E402

__all__ = ["get_current_time", "log_info", "log_warn", "log_error"]
"""Logging and time utilities for the server package.

These are functionally equivalent to the originals in the monolithic
`vpn-sentinel-server.py` but live under `vpn_sentinel_server` so they can be
tested and extended independently.
"""
from datetime import datetime
import zoneinfo
import os


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


def log_info(component: str, message: str) -> None:
    log_message("INFO", component, message)


def log_error(component: str, message: str) -> None:
    log_message("ERROR", component, message)


def log_warn(component: str, message: str) -> None:
    log_message("WARN", component, message)
