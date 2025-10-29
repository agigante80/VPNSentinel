"""Shared health helpers and schema for VPN Sentinel.

Provides a canonical JSON shape for /health-like endpoints and small helpers
to build and validate the structure. Keep this dependency-free and lightweight
so it can be imported in minimal test and runtime environments.

Schema (dict keys):
 - status: str ("ok" | "degraded" | "fail")
 - uptime_seconds: int
 - timestamp: ISO-8601 str (UTC)
 - components: dict mapping component name -> {status: str, details: dict}
 - server_time: ISO-8601 str (UTC)
 - version: optional str

The module provides:
 - make_health(status, uptime_seconds, components, version=None)
 - validate_health(obj) -> (bool, list[str])
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List, Optional


ALLOWED_STATUSES = {"ok", "degraded", "fail"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_health(
    status: str,
    uptime_seconds: int,
    components: Dict[str, Dict[str, Any]],
    version: Optional[str] = None,
) -> Dict[str, Any]:
    """Construct a canonical health JSON object.

    Args:
        status: overall status ('ok', 'degraded', 'fail')
        uptime_seconds: integer seconds since process start
        components: mapping of component -> {status: str, details: dict}
        version: optional version string

    Returns:
        dict with canonical health keys
    """
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"invalid status: {status}")

    # normalize components
    normalized: Dict[str, Dict[str, Any]] = {}
    for name, info in components.items():
        comp_status = info.get("status") if isinstance(info, dict) else None
        comp_details = info.get("details") if isinstance(info, dict) else {}
        if not comp_status or comp_status not in ALLOWED_STATUSES:
            raise ValueError(f"invalid component status for {name}: {comp_status}")
        normalized[name] = {"status": comp_status, "details": comp_details}

    return {
        "status": status,
        "uptime_seconds": int(uptime_seconds),
        "timestamp": _now_iso(),
        "components": normalized,
        "server_time": _now_iso(),
        **({"version": version} if version else {}),
    }


def validate_health(obj: Any) -> Tuple[bool, List[str]]:
    """Validate the health object shape. Returns (is_valid, errors).

    This is intentionally permissive: callers may allow additional keys, but
    basic structural checks are enforced.
    """
    errors: List[str] = []
    if not isinstance(obj, dict):
        return False, ["health object must be a dict"]

    # required root keys
    for key in ("status", "uptime_seconds", "timestamp", "components", "server_time"):
        if key not in obj:
            errors.append(f"missing key: {key}")

    # status
    status = obj.get("status")
    if status not in ALLOWED_STATUSES:
        errors.append(f"invalid status: {status}")

    # uptime_seconds
    uptime = obj.get("uptime_seconds")
    if not isinstance(uptime, int) or uptime < 0:
        errors.append("uptime_seconds must be a non-negative int")

    # timestamp and server_time: basic ISO-8601 check
    for ts_key in ("timestamp", "server_time"):
        ts = obj.get(ts_key)
        try:
            # try parsing: datetime.fromisoformat handles a wide range
            if not isinstance(ts, str):
                raise ValueError("not-a-string")
            datetime.fromisoformat(ts)
        except Exception:
            errors.append(f"{ts_key} is not a valid ISO-8601 string: {ts}")

    # components
    components = obj.get("components")
    if not isinstance(components, dict):
        errors.append("components must be a dict")
    else:
        for name, info in components.items():
            if not isinstance(info, dict):
                errors.append(f"component {name} info must be a dict")
                continue
            comp_status = info.get("status")
            if comp_status not in ALLOWED_STATUSES:
                errors.append(f"component {name} has invalid status: {comp_status}")

    return (len(errors) == 0, errors)


def sample_health_ok(version: Optional[str] = None) -> Dict[str, Any]:
    """Helper that returns a minimal 'ok' health object for tests and smoke checks."""
    components = {"api": {"status": "ok", "details": {}}}
    uptime = int(time.time() - STARTUP_AT) if "STARTUP_AT" in globals() else 0
    return make_health("ok", uptime, components, version=version)


# Optional module-level startup timestamp used in sample helpers during tests
STARTUP_AT = time.time()
