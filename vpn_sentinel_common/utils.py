"""Utility helpers shared across the project.

Provide a minimal, dependency-free implementation for escaping JSON strings
and sanitizing user-provided text. Kept intentionally small for tests and CI.
"""
from __future__ import annotations

import json
import re


def json_escape(s: str) -> str:
    """Return a JSON-escaped string suitable for embedding inside JSON literals.

    This mirrors the simple behavior expected by the client shim: ensure
    backslashes and double quotes are escaped. We use json.dumps and strip the
    surrounding quotes to be robust and correct for all control characters.
    """
    # json.dumps handles escaping reliably; strip the surrounding quotes
    return json.dumps(s)[1:-1]


# Precompiled regex to remove control characters (U+0000..U+001F)
_CTRL_RE = re.compile(r"[\x00-\x1F]")


def sanitize_string(s: str, max_len: int = 100) -> str:
    """Remove C0 control characters and truncate to max_len characters.

    The original shell fallback removed characters in range \x00-\x1F and
    limited output to 100 bytes. We keep the same behavior here.
    """
    if s is None:
        return ""
    cleaned = _CTRL_RE.sub("", s)
    if len(cleaned) > max_len:
        return cleaned[:max_len]
    return cleaned


__all__ = ["json_escape", "sanitize_string"]
