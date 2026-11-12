"""Canonical config helpers for VPN Sentinel shared library.

This module centralizes client configuration parsing and client-id generation.
It is intended to be imported by both server and client code.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import random
import time  # noqa: F401  # test-patching: tests patch config.time.time
from typing import Dict, Any


def secrets_match(provided: str, expected: str) -> bool:
    """Constant-time check that a presented secret equals the configured one.

    Both sides are hashed with SHA-256 first so the comparison is fixed-length
    (``hmac.compare_digest`` can leak length on unequal inputs). An empty value on
    either side never matches.

    WSGI decodes header bytes as latin-1 (PEP 3333), and which bytes a client sent
    for a non-ASCII secret depends on its library: urllib (the bundled client) sends
    latin-1, so the str IS the secret; UTF-8 clients (curl, Prometheus) arrive as
    mojibake that a latin-1 re-encode turns back into their bytes. Both readings are
    compared, always both, combined with ``|`` (not ``or``) so neither comparison is
    skipped; any remaining timing difference is a bool operation, far below network
    jitter. Only byte strings derived from the configured secret match.
    """
    if not provided or not expected:
        return False
    # surrogateescape: a secret read from env with undecodable bytes round-trips instead of raising.
    want = hashlib.sha256(expected.encode("utf-8", "surrogateescape")).digest()
    as_utf8 = provided.encode("utf-8", "surrogateescape")
    try:
        as_latin1 = provided.encode("latin-1")
    except UnicodeEncodeError:
        as_latin1 = b""  # sha256(b"") never equals the digest of a non-empty secret
    by_utf8 = hmac.compare_digest(hashlib.sha256(as_utf8).digest(), want)
    by_latin1 = hmac.compare_digest(hashlib.sha256(as_latin1).digest(), want)
    return by_utf8 | by_latin1


def read_secret(name: str, default: str = "") -> str:
    """Return a secret from ``NAME`` or, Docker style, from the file named by ``NAME_FILE``.

    Reads ``os.environ`` at call time. An empty ``NAME`` or ``NAME_FILE`` counts as unset
    (Compose injects ``NAME=`` empty when the host variable is unset). Setting both is an
    error, and so is a configured file that is unreadable, not UTF-8, or empty after all
    trailing CR/LF are stripped: an empty API key would otherwise mean "auth disabled".

    Raises:
        ValueError: with a message naming only the variable and path, never the content.
    """
    file_var = f"{name}_FILE"
    path = os.environ.get(file_var, "")
    value = os.environ.get(name, "")
    if path and value:
        raise ValueError(f"Both {name} and {file_var} are set; use one")
    if not path:
        return value or default
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError as e:
        raise ValueError(f"{file_var}={path} cannot be read: {e.strerror or type(e).__name__}") from None
    try:
        # utf-8-sig drops a leading BOM that Windows editors add; it would otherwise end up inside the secret.
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError(f"{file_var}={path} is not valid UTF-8") from None
    text = text.rstrip("\r\n")
    if not text:
        raise ValueError(f"{file_var}={path} is empty")
    return text


def _sanitize_client_id(cid: str) -> str:
    import re

    s = cid.lower()
    s = re.sub(r"[^a-z0-9-]", "-", s)
    s = re.sub(r"-+", "-", s)
    s = s.strip("-")
    return s or "sanitized-client"


def generate_client_id(env: Dict[str, str]) -> str:
    """Return a client id either from env or generated with random digits.

    Args:
        env: mapping of environment variables (use os.environ in production).

    Returns:
        Client ID in format: vpn-monitor-{12-random-digits}
    """
    if env.get("VPN_SENTINEL_CLIENT_ID"):
        cid = env["VPN_SENTINEL_CLIENT_ID"]
        if any(c for c in cid if not (c.islower() or c.isdigit() or c == "-")):
            return _sanitize_client_id(cid)
        return cid

    # Generate 12 random digits for client ID
    rand_digits = "".join(str(random.randint(0, 9)) for _ in range(12))
    return f"vpn-monitor-{rand_digits}"


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

    # Safely parse numeric values with sensible defaults if parsing fails
    def _safe_int(val, default):
        try:
            return int(val)
        except Exception:
            return default

    timeout = _safe_int(env.get("VPN_SENTINEL_TIMEOUT", env.get("TIMEOUT", 30)), 30)
    interval = _safe_int(env.get("VPN_SENTINEL_INTERVAL", env.get("INTERVAL", 300)), 300)

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
