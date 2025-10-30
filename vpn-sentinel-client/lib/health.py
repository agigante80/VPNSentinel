"""Thin delegating shim for health helpers.

Prefer importing the canonical implementation from ``vpn_sentinel_common.health``.
When that's not available (local dev/tests), try the lightweight
``vpn-sentinel-client/lib/health_common.py`` fallback. The shim exposes a small
CLI used by unit tests and by the shell wrapper.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple
import sys
import json

__all__ = [
    "check_client_process",
    "check_network_connectivity",
    "check_server_connectivity",
    "check_dns_leak_detection",
    "get_system_info",
    "generate_health_status",
]


def _load_canonical() -> Tuple[Optional[Callable], Optional[Callable], Optional[Callable], Optional[Callable], Optional[Callable], Optional[Callable]]:
    try:
        from vpn_sentinel_common.health import (
            check_client_process as _ccp,
            check_network_connectivity as _cnc,
            check_server_connectivity as _csc,
            check_dns_leak_detection as _cddl,
            get_system_info as _gsi,
            generate_health_status as _ghs,
        )

        return _ccp, _cnc, _csc, _cddl, _gsi, _ghs
    except Exception:
        return (None, None, None, None, None, None)


_ccp, _cnc, _csc, _cddl, _gsi, _ghs = _load_canonical()


def check_client_process() -> str:
    if _ccp:
        return _ccp()
    # fallback to local helper
    try:
        from vpn_sentinel_client.lib.health_common import check_client_process as _f
        return _f()
    except Exception:
        return "not_available"


def check_network_connectivity() -> str:
    if _cnc:
        return _cnc()
    try:
        from vpn_sentinel_client.lib.health_common import check_network_connectivity as _f
        return _f()
    except Exception:
        return "unreachable"


def check_server_connectivity() -> str:
    if _csc:
        return _csc()
    try:
        from vpn_sentinel_client.lib.health_common import check_server_connectivity as _f
        return _f()
    except Exception:
        return "not_configured"


def check_dns_leak_detection() -> str:
    if _cddl:
        return _cddl()
    try:
        from vpn_sentinel_client.lib.health_common import check_dns_leak_detection as _f
        return _f()
    except Exception:
        return "unavailable"


def get_system_info() -> Dict[str, Any]:
    if _gsi:
        return _gsi()
    try:
        from vpn_sentinel_client.lib.health_common import get_system_info as _f
        return _f()
    except Exception:
        return {"memory_percent": "unknown", "disk_percent": "unknown"}


def generate_health_status() -> Dict[str, Any]:
    if _ghs:
        return _ghs()
    try:
        from vpn_sentinel_client.lib.health_common import generate_health_status as _f
        return _f()
    except Exception:
        return {"status": "unknown", "checks": {}, "system": {}, "issues": []}


def _cli() -> None:
    data = {
        "client_process": check_client_process(),
        "network_connectivity": check_network_connectivity(),
        "dns_leak_detection": check_dns_leak_detection(),
    }
    print(json.dumps(data))


if __name__ == "__main__":
    _cli()
