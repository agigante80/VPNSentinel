"""Small logging helpers used across the project.

Keep this intentionally tiny and dependency-free so tests and CI can import it
without adding runtime dependencies.
"""
from __future__ import annotations

import logging as std_logging
import sys
from datetime import datetime
import zoneinfo
import os


# Global file handle for log file (if configured)
_log_file_handle = None


def _configure_once():
    # Basic config: stream to stdout with human-friendly format.
    if not std_logging.getLogger().handlers:
        std_logging.basicConfig(
            level=std_logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
            handlers=[std_logging.StreamHandler(sys.stdout)],
        )


def _initialize_log_file():
    """Initialize log file if VPN_SENTINEL_LOG_FILE is set."""
    global _log_file_handle
    
    if _log_file_handle is not None:
        return  # Already initialized
    
    log_file_path = os.getenv('VPN_SENTINEL_LOG_FILE')
    if not log_file_path:
        return  # No log file configured
    
    try:
        # Ensure parent directory exists
        log_dir = os.path.dirname(log_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Open log file in append mode with line buffering
        _log_file_handle = open(log_file_path, 'a', buffering=1, encoding='utf-8')
    except Exception as e:
        # Log error to stderr but don't fail
        print(f"WARNING: Could not open log file {log_file_path}: {e}", file=sys.stderr, flush=True)


def get_current_time():
    """Get current time in configured timezone.

    Returns a timezone-aware datetime similar to the legacy implementation.
    """
    tz = zoneinfo.ZoneInfo(os.getenv('TZ', 'UTC'))
    return datetime.now(tz)


def log_message(level: str, component: str, message: str) -> None:
    """Log a message with structured format: timestamp level [component] message."""
    # Initialize log file on first use
    _initialize_log_file()
    
    timestamp = datetime.now(zoneinfo.ZoneInfo("UTC")).strftime('%Y-%m-%dT%H:%M:%SZ')
    log_line = f"{timestamp} {level} [{component}] {message}"
    
    # Always log to stdout
    print(log_line, flush=True)
    
    # Also log to file if configured
    if _log_file_handle:
        try:
            _log_file_handle.write(log_line + '\n')
            _log_file_handle.flush()
        except Exception:
            # Silently ignore file write errors to avoid breaking the application
            pass


def log_info(component: str, msg: str) -> None:
    """Log info message with timestamp."""
    log_message("INFO", component, msg)


def log_error(component: str, msg: str) -> None:
    """Log error message with timestamp."""
    log_message("ERROR", component, msg)


def log_warn(component: str, msg: str) -> None:
    """Log warning message with timestamp."""
    log_message("WARN", component, msg)
