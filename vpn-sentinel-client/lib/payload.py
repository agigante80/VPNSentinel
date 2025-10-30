#!/usr/bin/env python3
from __future__ import annotations

"""Minimal payload CLI shim used by tests and legacy scripts.

Behavior:
- --build-json: prints a JSON payload built from environment variables
- --post: reads JSON from stdin and writes compact JSON to VPN_SENTINEL_TEST_CAPTURE_PATH if set

This intentionally stays small to make later removal low-risk.
"""

import argparse
import json
import sys
import os
from typing import Dict, Any
from datetime import datetime


_USING_CANONICAL = False
try:
    from vpn_sentinel_common.payload import (
        build_payload_from_env as _build_payload_from_env,
        post_payload as _post_payload,
    )
    _USING_CANONICAL = True
except Exception:
    _USING_CANONICAL = False


def build_payload_from_env() -> Dict[str, Any]:
    if _USING_CANONICAL:
        return _build_payload_from_env()
    ts = datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    return {
        "client_id": os.environ.get("CLIENT_ID", os.environ.get("VPN_SENTINEL_CLIENT_ID", "")),
        "timestamp": ts,
        "public_ip": os.environ.get("PUBLIC_IP", "unknown"),
        "status": "alive",
        "location": {
            "country": os.environ.get("COUNTRY", "Unknown"),
            "city": os.environ.get("CITY", "Unknown"),
            "region": os.environ.get("REGION", "Unknown"),
            "org": os.environ.get("ORG", "Unknown"),
            "timezone": os.environ.get("VPN_TIMEZONE", "Unknown"),
        },
        "dns_test": {
            "location": os.environ.get("DNS_LOC", "Unknown"),
            "colo": os.environ.get("DNS_COLO", "Unknown"),
        },
    }


def post_payload(payload_text: str) -> int:
    if _USING_CANONICAL:
        return _post_payload(payload_text)
    capture = os.environ.get("VPN_SENTINEL_TEST_CAPTURE_PATH")
    if not capture:
        return 1
    try:
        os.makedirs(os.path.dirname(capture), exist_ok=True)
    except Exception:
        pass
    try:
        obj = json.loads(payload_text)
        with open(capture, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, separators=(",", ":")))
            f.write("\n")
        return 0
    except Exception:
        try:
            line = " ".join(payload_text.splitlines())
            with open(capture, "a", encoding="utf-8") as f:
                f.write(line + "\n")
            return 0
        except Exception:
            return 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="payload.py")
    p.add_argument("--build-json", action="store_true", help="Build JSON payload from environment and print it")
    p.add_argument("--post", action="store_true", help="Post a JSON payload read from stdin to the server or test capture path")
    args = p.parse_args(argv)

    if args.build_json:
        payload = build_payload_from_env()
        sys.stdout.write(json.dumps(payload, ensure_ascii=False))
        return 0

    if args.post:
        data = sys.stdin.read()
        return post_payload(data)

    p.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
