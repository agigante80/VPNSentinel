"""Thin client shim: re-export canonical config helpers from vpn_sentinel_common.

This module intentionally re-exports the canonical functions from
`vpn_sentinel_common.config`. During migration we keep this file to avoid
changing import paths across the codebase; it is expected to be removed once
all callers import `vpn_sentinel_common.config` directly.
"""
from __future__ import annotations

from typing import Dict, Any

from vpn_sentinel_common.config import load_config, generate_client_id  # type: ignore

__all__ = ["load_config", "generate_client_id"]
