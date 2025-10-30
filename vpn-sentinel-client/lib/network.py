"""Thin shim: re-export canonical network helpers from vpn_sentinel_common.

This keeps import paths stable while we migrate callers to import the
shared implementation directly.
"""
from __future__ import annotations

from typing import Dict

__all__ = ["parse_geolocation", "parse_dns_trace"]

try:
	from vpn_sentinel_common.network import parse_geolocation, parse_dns_trace  # type: ignore
except Exception:
	# Lightweight fallback implementations used when the shared package is
	# not installed in the environment (e.g., local unit tests). These mirror
	# the canonical behavior enough for the test-suite and the shell shim's
	# CLI usage.
	import sys
	import json


	def parse_geolocation(json_text: str, source: str = "auto") -> Dict[str, str]:
		try:
			j = json.loads(json_text)
		except Exception:
			return {}
		# Map common fields used by the client script
		return {
			"ip": j.get("ip") or j.get("query"),
			"country": j.get("country") or j.get("countryCode"),
			"city": j.get("city"),
			"region": j.get("region") or j.get("regionName"),
			"org": j.get("org") or j.get("isp"),
			"timezone": j.get("timezone"),
		}


	def parse_dns_trace(trace_text: str) -> Dict[str, str]:
		# simple key=value lines expected by tests: loc=LA\ncolo=la1\n...
		out = {}
		for line in trace_text.splitlines():
			if '=' in line:
				k, v = line.split('=', 1)
				out[k.strip()] = v.strip()
		return out


	def _cli_main() -> None:
		data = sys.stdin.read()
		if len(sys.argv) > 1 and sys.argv[1] == "--dns":
			print(json.dumps(parse_dns_trace(data)))
		else:
			print(json.dumps(parse_geolocation(data)))


	if __name__ == "__main__":
		_cli_main()
