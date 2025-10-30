"""Client-side shim for network helpers.

Prefers to import canonical implementations from
`vpn_sentinel_common.network`. Falls back to local parsing helpers if the
common package isn't available (useful for tests).
"""
from __future__ import annotations

from typing import Dict

try:
    from vpn_sentinel_common.network import parse_geolocation, parse_dns_trace  # type: ignore
except Exception:  # pragma: no cover - fallback used in isolated tests
    import json


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

        
# CLI helper is intentionally defined at module level so the script will
# emit JSON whether it uses the canonical implementation (imported above)
# or the fallback versions defined in the except block.


def _cli_print_json() -> None:
    """Read stdin (geolocation json or dns trace) and print parsed JSON for shell callers.

    If invoked with --dns, read a dns trace from stdin and print parsed DNS info.
    Otherwise read a geolocation JSON blob from stdin and print parsed geolocation.
    """
    import json
    import sys

    if "--dns" in sys.argv:
        data = sys.stdin.read()
        parsed = parse_dns_trace(data or "")
        print(json.dumps(parsed))
        return

    # default: geolocation parse
    text = sys.stdin.read()
    parsed = parse_geolocation(text or "")
    print(json.dumps(parsed))


if __name__ == "__main__":
    _cli_print_json()
