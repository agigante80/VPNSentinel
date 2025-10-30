#!/usr/bin/env python3
"""Compatibility shim for payload: delegate to vpn_sentinel_common.payload when available.

This keeps the same CLI contract expected by tests and legacy callers while the
canonical implementation lives in `vpn_sentinel_common.payload`.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Dict, Any


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
    # Minimal local fallback (rare in tests because common is present)
    import os
    from datetime import datetime

    ts = datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    payload = {
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
    return payload


def post_payload(payload_text: str) -> int:
    if _USING_CANONICAL:
        return _post_payload(payload_text)
    # Fallback: write to capture path if set
    import os

    capture = os.environ.get("VPN_SENTINEL_TEST_CAPTURE_PATH")
    if capture:
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
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any


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
    payload = {
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
    return payload


def post_payload(payload_text: str) -> int:
    if _USING_CANONICAL:
        return _post_payload(payload_text)
    # Test capture path takes precedence
    capture = os.environ.get("VPN_SENTINEL_TEST_CAPTURE_PATH")
    if capture:
        try:
            os.makedirs(os.path.dirname(capture), exist_ok=True)
        except Exception:
            pass
        try:
            # Write compact JSON as a single line
            obj = json.loads(payload_text)
            with open(capture, "a", encoding="utf-8") as f:
                f.write(json.dumps(obj, separators=(",", ":")))
                f.write("\n")
            return 0
        except Exception:
            # fallback: write raw payload condensed
            try:
                line = " ".join(payload_text.splitlines())
                with open(capture, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
                return 0
            except Exception:
                return 1

    # Otherwise POST to server URL
    import urllib.request

    server_url = os.environ.get("SERVER_URL")
    if not server_url:
        base = os.environ.get("VPN_SENTINEL_URL", "http://your-server-url:5000")
        api_path = os.environ.get("VPN_SENTINEL_API_PATH", "/api/v1")
        server_url = f"{base.rstrip('/')} {api_path.rstrip('/')}/keepalive"
    else:
        server_url = server_url.rstrip("/") + "/keepalive"

    api_key = os.environ.get("VPN_SENTINEL_API_KEY")
    timeout = float(os.environ.get("TIMEOUT", os.environ.get("VPN_SENTINEL_TIMEOUT", "30")))

    data = payload_text.encode("utf-8")
    req = urllib.request.Request(server_url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.getcode()
            if 200 <= code < 300:
                return 0
            return 1
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

# shim marker


if __name__ == "__main__":
    raise SystemExit(main())

# shim marker
