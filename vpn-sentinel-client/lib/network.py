"""Thin shim: re-export canonical network helpers from vpn_sentinel_common.

This keeps import paths stable while we migrate callers to import the
shared implementation directly.
"""
from __future__ import annotations

from typing import Dict

from vpn_sentinel_common.network import parse_geolocation, parse_dns_trace  # type: ignore

__all__ = ["parse_geolocation", "parse_dns_trace"]
