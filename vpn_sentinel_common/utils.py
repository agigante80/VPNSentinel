"""Utility helpers shared across the project.

Provide a minimal, dependency-free implementation for small helpers used by
client shims and tests: time/log delegations (thin), JSON escaping and
sanitization helpers.
"""
from __future__ import annotations

from typing import Any
import json
import re

from .logging import get_current_time as _get_current_time
from .logging import log_info as _log_info, log_warn as _log_warn, log_error as _log_error


def get_current_time() -> Any:
    """Return the current timezone-aware datetime.

    Delegates to the canonical logging/time helper.
    """
    return _get_current_time()


def log_info(component: str, message: str) -> None:
    _log_info(component, message)


def log_warn(component: str, message: str) -> None:
    _log_warn(component, message)


def log_error(component: str, message: str) -> None:
    _log_error(component, message)


def json_escape(s: str) -> str:
    """Return a JSON-escaped string suitable for embedding inside JSON literals.

    We use json.dumps and strip the surrounding quotes to be robust for all
    control characters.
    """
    return json.dumps(s)[1:-1]


# Precompiled regex to remove control characters (U+0000..U+001F)
_CTRL_RE = re.compile(r"[\x00-\x1F]")


def sanitize_string(s: str, max_len: int = 100) -> str:
    """Remove C0 control characters and truncate to max_len characters."""
    if s is None:
        return ""
    cleaned = _CTRL_RE.sub("", s)
    if len(cleaned) > max_len:
        return cleaned[:max_len]
    return cleaned


__all__ = ["get_current_time", "log_info", "log_warn", "log_error", "json_escape", "sanitize_string"]
