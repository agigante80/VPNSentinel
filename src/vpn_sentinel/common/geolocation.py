"""Geolocation helpers shared between client and server.

This module provides a small, testable interface to query public IP and
location information using a primary provider and fallbacks. It mirrors the
behaviour of the existing shell client (ipinfo.io -> ip-api.com -> ipwhois.app)
but is intentionally small and dependency-free (uses requests when available,
falls back to urllib).

Functions:
 - get_geolocation(service='auto', timeout=5) -> dict

Returned dict keys: public_ip, country, city, region, org, timezone, source
If lookup fails, returns an empty dict.
"""
from __future__ import annotations

import json
import socket
from typing import Dict, Optional

try:
    import requests
except Exception:
    requests = None

DEFAULT_PROVIDERS = ["ipinfo.io", "ip-api.com", "ipwhois.app"]


def _http_get(url: str, timeout: int) -> Optional[str]:
    try:
        if requests:
            r = requests.get(url, timeout=timeout)
            if r.status_code == 200:
                return r.text
            return None
        # fallback to urllib
        from urllib.request import urlopen

        with urlopen(url, timeout=timeout) as fh:
            return fh.read().decode("utf-8")
    except Exception:
        return None


def _parse_ipinfo(text: str) -> Dict[str, str]:
    data = json.loads(text)
    return {
        "public_ip": data.get("ip", ""),
        "country": data.get("country", ""),
        "city": data.get("city", ""),
        "region": data.get("region", ""),
        "org": data.get("org", ""),
        "timezone": data.get("timezone", ""),
    }


def _parse_ip_api(text: str) -> Dict[str, str]:
    data = json.loads(text)
    return {
        "public_ip": data.get("query", "") or data.get("ip", ""),
        "country": data.get("country", ""),
        "city": data.get("city", ""),
        "region": data.get("regionName", "") or data.get("region", ""),
        "org": data.get("isp", "") or data.get("org", ""),
        "timezone": data.get("timezone", ""),
    }


def _parse_ipwhois(text: str) -> Dict[str, str]:
    data = json.loads(text)
    # ipwhois.app returns a slightly different shape; best-effort mapping
    return {
        "public_ip": data.get("ip", ""),
        "country": data.get("country", ""),
        "city": data.get("city", ""),
        "region": data.get("region", ""),
        "org": data.get("org", "") or data.get("asn", {}).get("name", ""),
        "timezone": data.get("timezone", ""),
    }


PARSERS = {
    "ipinfo.io": ("https://ipinfo.io/json", _parse_ipinfo),
    "ip-api.com": ("http://ip-api.com/json", _parse_ip_api),
    "ipwhois.app": ("https://ipwhois.app/json/", _parse_ipwhois),
}


def get_geolocation(service: str = "auto", timeout: int = 5) -> Dict[str, str]:
    """Return geolocation data as a dict.

    Args:
        service: 'auto' or one of the provider keys: ipinfo.io, ip-api.com, ipwhois.app
        timeout: request timeout in seconds

    Returns:
        dict with keys: public_ip, country, city, region, org, timezone, source
        or empty dict on failure.
    """
    providers = []
    if service == "auto":
        providers = DEFAULT_PROVIDERS
    elif service in PARSERS:
        providers = [service]
    else:
        # unknown service
        return {}

    for p in providers:
        url, parser = PARSERS[p]
        body = _http_get(url, timeout)
        if not body:
            continue
        try:
            parsed = parser(body)
            if parsed.get("public_ip"):
                parsed["source"] = p
                return parsed
        except Exception:
            # try next
            continue

    return {}
