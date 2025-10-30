"""Thin CLI shim that delegates to vpn_sentinel_common.geolocation.get_geolocation.

Remains for compatibility while callers migrate to import the shared module
or prefer `python -m vpn_sentinel_common.geolocation` if a CLI entrypoint is
added there.
"""
from __future__ import annotations

from vpn_sentinel_common.geolocation import get_geolocation  # type: ignore

__all__ = ["get_geolocation"]
