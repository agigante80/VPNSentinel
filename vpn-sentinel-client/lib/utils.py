#!/usr/bin/env python3
"""Small utils shim for vpn-sentinel-client to replace utils.sh at runtime.

Provides `json_escape` and `sanitize_string` via a CLI so shell callers can
invoke it when Python is preferred.
"""
from __future__ import annotations

import sys
import json
import re


def json_escape(s: str) -> str:
    return s.replace('\\', '\\\\').replace('"', '\\"')


def sanitize_string(s: str) -> str:
    # remove control chars and limit to 100 chars
    s = re.sub(r"[\x00-\x1f]+", "", s)
    return s[:100]


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
        # Accept a json payload like {"op":"sanitize","value":"..."}
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
