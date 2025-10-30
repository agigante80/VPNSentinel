"""Client-side shim for configuration helpers.

This module prefers to import canonical implementations from
`vpn_sentinel_common.config`. If the common package is not available (e.g.
in tests that import the shim directly), the local implementations act as
fallbacks to preserve compatibility.
"""
from __future__ import annotations

from typing import Dict, Any

try:  # prefer canonical shared module
    from vpn_sentinel_common.config import load_config, generate_client_id  # type: ignore
except Exception:  # pragma: no cover - fallback for test harnesses
    import random
    import time


    def _sanitize_client_id(cid: str) -> str:
        import re

        s = cid.lower()
        s = re.sub(r"[^a-z0-9-]", "-", s)
        s = re.sub(r"-+", "-", s)
        s = s.strip("-")
        return s or "sanitized-client"


    def generate_client_id(env: Dict[str, str]) -> str:
        if env.get("VPN_SENTINEL_CLIENT_ID"):
            cid = env["VPN_SENTINEL_CLIENT_ID"]
            if any(c for c in cid if not (c.islower() or c.isdigit() or c == "-")):
                return _sanitize_client_id(cid)
            return cid

        timestamp_part = str(int(time.time()))
        timestamp_part = timestamp_part[-7:]
        rand_part = f"{random.randint(100000,999999):06d}"
        return f"vpn-client-{timestamp_part}{rand_part}"


    def load_config(env: Dict[str, str]) -> Dict[str, Any]:
        version = env.get("VERSION")
        if not version:
            commit = env.get("COMMIT_HASH")
            version = f"1.0.0-dev-{commit}" if commit else "1.0.0-dev"

        api_base = env.get("VPN_SENTINEL_URL", "http://your-server-url:5000")
        api_path = env.get("VPN_SENTINEL_API_PATH", "/api/v1") or "/api/v1"
        if not api_path.startswith("/"):
            api_path = "/" + api_path
        server_url = f"{api_base}{api_path}"

        is_https = api_base.startswith("https://")

        timeout = int(env.get("VPN_SENTINEL_TIMEOUT", env.get("TIMEOUT", 30)))
        interval = int(env.get("VPN_SENTINEL_INTERVAL", env.get("INTERVAL", 300)))

        client_id = generate_client_id(env)

        tls_cert_path = env.get("VPN_SENTINEL_TLS_CERT_PATH", "")
        allow_insecure = env.get("VPN_SENTINEL_ALLOW_INSECURE", "false").lower() == "true"

        debug = env.get("VPN_SENTINEL_DEBUG", "false").lower() == "true"

        return {
            "version": version,
            "api_base": api_base,
            "api_path": api_path,
            "server_url": server_url,
            "is_https": is_https,
            "timeout": timeout,
            "interval": interval,
            "client_id": client_id,
            "tls_cert_path": tls_cert_path,
            "allow_insecure": allow_insecure,
            "debug": debug,
        }
