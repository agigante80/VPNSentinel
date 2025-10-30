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
    out = {"loc": "", "colo": ""}
    if not trace_text:
        return out
    for line in trace_text.splitlines():
        if line.startswith("loc="):
            out["loc"] = line.split("=", 1)[1]
        elif line.startswith("colo="):
            out["colo"] = line.split("=", 1)[1]
    return out
