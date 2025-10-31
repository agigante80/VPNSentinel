#!/usr/bin/env python3
"""Thin delegating shim for utils helpers.

Prefer the canonical implementation `vpn_sentinel_common.utils`. When the
canonical package isn't available (local dev/test), provide a lightweight
fallback to keep runtime behavior stable.

This file exposes a small CLI used by the shell wrapper and unit tests.
"""
from __future__ import annotations

import sys
import json
from typing import Callable
# This shim now assumes the canonical package is available in CI and
# builds. Import directly and let import errors surface during dev if
# the package isn't installed (developer should use editable install).
from vpn_sentinel_common.utils import json_escape as _json_escape, sanitize_string as _sanitize_string  # type: ignore


def json_escape(s: str) -> str:
    return _json_escape(s)


def sanitize_string(s: str) -> str:
    return _sanitize_string(s)


def main(argv: list[str] | None = None) -> int:
    argv = list(argv or sys.argv[1:])
    if not argv or argv[0] in ("-h", "--help"):
        print("Usage: utils.py --json-escape <string> | --sanitize <string>")
        return 0
    if argv[0] == "--json-escape" and len(argv) >= 2:
        print(json_escape(argv[1]))
        return 0
    if argv[0] == "--sanitize" and len(argv) >= 2:
        print(sanitize_string(argv[1]))
        return 0
    if argv[0] == "--json" and len(argv) >= 2:
        try:
            payload = json.loads(argv[1])
            op = payload.get("op")
            val = payload.get("value", "")
            if op == "sanitize":
                print(sanitize_string(val))
                return 0
            if op == "escape":
                print(json_escape(val))
                return 0
        except Exception:
            print("Invalid JSON payload", file=sys.stderr)
            return 2
    print("Invalid args", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
