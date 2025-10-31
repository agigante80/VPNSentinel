#!/usr/bin/env python3
"""Small CLI shim that delegates logging calls to vpn_sentinel_common.logging.

The client shell script calls this file with --json '{"level":"INFO",...}'
so we accept a --json payload, parse it, and route to the canonical logging
helpers. Keep behavior minimal and dependency-free (vpn_sentinel_common is in
repo and installed in CI/venv).
"""
from __future__ import annotations

import argparse
import json
import sys

from vpn_sentinel_common.logging import log_info, log_warn, log_error


def main(argv: list[str] | None = None) -> int:
    argv = list(argv or sys.argv[1:])
    parser = argparse.ArgumentParser(prog="log.py")
    parser.add_argument("--json", dest="payload", help="JSON payload with level,component,message")
    args = parser.parse_args(argv)
    if not args.payload:
        return 0
    try:
        obj = json.loads(args.payload)
    except Exception:
        return 2
    level = (obj.get("level") or "INFO").upper()
    component = obj.get("component") or ""
    message = obj.get("message") or ""
    if level == "INFO":
        log_info(component, message)
    elif level == "WARN":
        log_warn(component, message)
    else:
        log_error(component, message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
#!/usr/bin/env python3
"""Minimal log shim for vpn-sentinel-client to replace log.sh at runtime.

This module is intentionally small: the shell runtime calls the logging
functions for structured messages in a human-readable format. The shim
supports a simple CLI so caller scripts can invoke it when Python is
preferred in the environment.
"""
from __future__ import annotations

import sys
import json
from datetime import datetime


def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def log(level: str, component: str, message: str) -> None:
    print(f"{_timestamp()} {level} [{component}] {message}")


def main(argv: list[str] | None = None) -> int:
    argv = list(argv or sys.argv[1:])
    if not argv or argv[0] in ("-h", "--help"):
        print("Usage: log.py LEVEL COMPONENT MESSAGE")
        return 0
    # Accept JSON input mode: --json '{"level":"INFO","component":"x","message":"y"}'
    if argv[0] == "--json" and len(argv) >= 2:
        try:
            payload = json.loads(argv[1])
            log(payload.get("level", "INFO"), payload.get("component", ""), payload.get("message", ""))
            return 0
        except Exception:
            print("Invalid JSON payload", file=sys.stderr)
            return 2
    if len(argv) < 3:
        print("Too few args", file=sys.stderr)
        return 2
    level, component = argv[0], argv[1]
    message = " ".join(argv[2:])
    log(level, component, message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# shim marker
