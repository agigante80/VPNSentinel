"""Canonical payload helpers for vpn_sentinel_common.

Provides build_payload_from_env() and post_payload() so clients and server
can import a single source of truth instead of duplicating logic in the
client shim.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict


def build_payload_from_env() -> Dict[str, Any]:
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
    """Post a payload or write it to a test capture path.

    Returns 0 on success, non-zero on failure. This mirrors the client shim
    behaviour and intentionally keeps behavior stable for tests.
    """
    # Test capture path takes precedence
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

    # Otherwise POST to server URL
    import urllib.request

    server_url = os.environ.get("SERVER_URL")
    if not server_url:
        base = os.environ.get("VPN_SENTINEL_URL", "http://your-server-url:5000")
        api_path = os.environ.get("VPN_SENTINEL_API_PATH", "/api/v1")
        server_url = f"{base.rstrip('/')}" + f"{api_path.rstrip('/')}/keepalive"
    else:
        server_url = server_url.rstrip("/") + "/keepalive"

    api_key = os.environ.get("VPN_SENTINEL_API_KEY")
    timeout = float(os.environ.get("TIMEOUT", os.environ.get("VPN_SENTINEL_TIMEOUT", "30")))

    data = payload_text.encode("utf-8")
    req = urllib.request.Request(server_url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if api_key:
        req.add_header("X-API-Key", api_key)

    try:
        # Respect TLS configuration: allow insecure or provide a CA bundle
        import ssl

        allow_insecure = os.environ.get("VPN_SENTINEL_ALLOW_INSECURE", "false").lower() == "true"
        tls_cert = os.environ.get("VPN_SENTINEL_TLS_CERT_PATH", "")
        ctx = None
        if allow_insecure:
            ctx = ssl._create_unverified_context()
        elif tls_cert:
            try:
                ctx = ssl.create_default_context(cafile=tls_cert)
            except Exception:
                # fallback to default context if loading CA failed
                ctx = ssl.create_default_context()

        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            code = resp.getcode()
            if 200 <= code < 300:
                return 0
            return 1
    except Exception:
        return 1
