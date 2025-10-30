"""Thin delegating shim for network helpers.

Prefer importing the canonical implementation from vpn_sentinel_common.network.
When that's not available (local dev/tests), provide lightweight fallbacks and
preserve a small CLI used by unit tests and the shell wrapper.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple, Callable

__all__ = ["parse_geolocation", "parse_dns_trace"]


def _load_canonical() -> Tuple[Optional[Callable], Optional[Callable]]:
    try:
        # Import here to keep import-time side-effects minimal for tests.
        from vpn_sentinel_common.network import parse_geolocation as _pg, parse_dns_trace as _pd  # type: ignore

        return _pg, _pd
    except Exception:
        return None, None


_parse_geolocation, _parse_dns_trace = _load_canonical()


def parse_geolocation(json_text: str, source: str = "auto") -> Dict[str, str]:
    """Parse provider geolocation JSON into the small mapping the client expects.

    If the canonical implementation is available use it; otherwise use a
    minimal, forgiving parser sufficient for tests and for the shell wrapper.
    """
    if _parse_geolocation:
        return _parse_geolocation(json_text, source=source)

    import json

    try:
        j = json.loads(json_text)
    except Exception:
        return {}
    return {
        "ip": j.get("ip") or j.get("query"),
        "country": j.get("country") or j.get("countryCode"),
        "city": j.get("city"),
        "region": j.get("region") or j.get("regionName"),
        "org": j.get("org") or j.get("isp"),
        "timezone": j.get("timezone"),
    }


def parse_dns_trace(trace_text: str) -> Dict[str, str]:
    """Parse a simple dns trace (key=value lines) into a dict.

    Delegates to canonical implementation when available.
    """
    if _parse_dns_trace:
        return _parse_dns_trace(trace_text)

    out: Dict[str, str] = {}
    for line in trace_text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


if __name__ == "__main__":
    # Provide a small CLI used by unit tests / shell wrapper: read stdin and
    # output JSON for either geolocation or dns (--dns) mode.
    import sys
    import json

    data = sys.stdin.read()
    if len(sys.argv) > 1 and sys.argv[1] == "--dns":
        print(json.dumps(parse_dns_trace(data)))
    else:
        print(json.dumps(parse_geolocation(data)))
