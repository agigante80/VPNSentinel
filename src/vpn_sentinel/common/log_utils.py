"""Small logging helpers used across the project.

Keep this intentionally tiny and dependency-free so tests and CI can import it
without adding runtime dependencies.
"""
from __future__ import annotations

import logging as std_logging
from logging.handlers import RotatingFileHandler
import sys
from datetime import datetime
import zoneinfo
import os


# Global file handle for log file (if configured)
_log_file_handle = None

# Log rotation configuration (can be overridden via environment variables)
MAX_LOG_SIZE_BYTES = int(os.getenv('VPN_SENTINEL_LOG_MAX_SIZE', str(10 * 1024 * 1024)))  # 10 MB default
MAX_LOG_BACKUPS = int(os.getenv('VPN_SENTINEL_LOG_MAX_BACKUPS', '5'))  # 5 backup files default


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
    """Initialize log file with rotation. Uses VPN_SENTINEL_LOG_FILE env var or defaults to /tmp/vpn-sentinel-server.log.
    
    Log rotation prevents unlimited disk space usage:
    - Max file size: 10 MB (configurable via VPN_SENTINEL_LOG_MAX_SIZE)
    - Backup files: 5 (configurable via VPN_SENTINEL_LOG_MAX_BACKUPS)
    - Total max disk usage: ~60 MB (10 MB × 6 files)
    """
    global _log_file_handle
    
    if _log_file_handle is not None:
        return  # Already initialized
    
    # Use configured path or default to /tmp
    log_file_path = os.getenv('VPN_SENTINEL_LOG_FILE', '/tmp/vpn-sentinel-server.log')
    if not log_file_path:
        return  # Empty string means explicitly disabled
    
    try:
        # Ensure parent directory exists
        log_dir = os.path.dirname(log_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Create rotating file handler
        # This automatically rotates logs when size limit is reached
        handler = RotatingFileHandler(
            log_file_path,
            maxBytes=MAX_LOG_SIZE_BYTES,
            backupCount=MAX_LOG_BACKUPS,
            encoding='utf-8'
        )
        
        # Set formatter to just output the message (already formatted)
        formatter = std_logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        
        # Store the handler (not a plain file handle)
        _log_file_handle = handler
        
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
            # Create a log record for the rotating handler
            record = std_logging.LogRecord(
                name='vpn_sentinel',
                level=std_logging.INFO,
                pathname='',
                lineno=0,
                msg=log_line,
                args=(),
                exc_info=None
            )
            _log_file_handle.emit(record)
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
