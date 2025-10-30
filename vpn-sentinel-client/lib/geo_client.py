"""Geo shim used by the client during migration.

Prefer the canonical implementation in `vpn_sentinel_common.geolocation` if
available, otherwise provide a tiny fallback so callers (and tests) continue
to work in environments where the package hasn't been installed.
"""

from __future__ import annotations

from typing import Dict

_USING_CANONICAL = False
try:
	from vpn_sentinel_common.geolocation import get_geolocation as _get_geolocation  # type: ignore
	_USING_CANONICAL = True
except Exception:
	_USING_CANONICAL = False


def get_geolocation(service: str = "auto", timeout: int = 5) -> Dict[str, str]:
	"""Return a geolocation dict.

	When the canonical package is present this delegates to that function.
	Otherwise, return a minimal, well-formed dict used by callers/tests.
	"""
	if _USING_CANONICAL:
		return _get_geolocation(service=service, timeout=timeout)

	# Minimal best-effort fallback: return unknowns so callers can continue.
	return {
		"ip": "unknown",
		"country": "Unknown",
		"region": "Unknown",
		"city": "Unknown",
		"timezone": "UTC",
	}


__all__ = ["get_geolocation"]
