"""Canonical network helpers for VPN Sentinel shared library.

Provides geolocation parsing and DNS trace parsing utilities.
"""
from __future__ import annotations

import json
from typing import Dict


def parse_geolocation(json_text: str, source: str = "ipinfo.io") -> Dict[str, str]:
    try:
        data = json.loads(json_text)
    except Exception:
        return {"ip": "", "country": "", "city": "", "region": "", "org": "", "timezone": ""}

    if source == "ip-api.com":
        return {
            "ip": data.get("query", "") or "",
            "country": data.get("countryCode", "") or "",
            "city": data.get("city", "") or "",
            "region": data.get("regionName", "") or "",
            "org": data.get("isp", "") or "",
            "timezone": data.get("timezone", "") or "",
        }

    return {
        "ip": data.get("ip", "") or "",
        "country": data.get("country", "") or "",
        "city": data.get("city", "") or "",
        "region": data.get("region", "") or "",
        "org": data.get("org", "") or "",
        "timezone": data.get("timezone", "") or "",
    }


def parse_dns_trace(trace_text: str) -> Dict[str, str]:
    """Parse DNS trace response from Cloudflare whoami service.
    
    Handles both formats:
    - Single line: "fl=... ip=... loc=XX colo=YYY ..."
    - Multi-line: loc=XX\ncolo=YYY
    """
    out = {"loc": "", "colo": ""}
    if not trace_text:
        return out
    
    # Remove quotes if present (Cloudflare returns quoted string)
    trace_text = trace_text.strip('"')
    
    # Try to parse as space-separated key=value pairs (Cloudflare format)
    for pair in trace_text.split():
        if '=' in pair:
            key, value = pair.split('=', 1)
            if key == 'loc':
                out['loc'] = value
            elif key == 'colo':
                out['colo'] = value
    
    # Also check line-by-line format (legacy compatibility)
    if not out['loc'] and not out['colo']:
        for line in trace_text.splitlines():
            if line.startswith("loc="):
                out["loc"] = line.split("=", 1)[1]
            elif line.startswith("colo="):
                out["colo"] = line.split("=", 1)[1]
    
    return out
