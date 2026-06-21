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
import os
import subprocess
import shutil

try:
    import psutil
except Exception:
    psutil = None

try:
    import requests
except Exception:
    requests = None


ALLOWED_STATUSES = {"ok", "degraded", "fail"}
# accept 'warn' as a historical alias for 'degraded'
ALIAS_MAP = {"warn": "degraded"}


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
    # normalize overall status (allow alias like 'warn')
    status_norm = (status or "").lower()
    if status_norm in ALIAS_MAP:
        status_norm = ALIAS_MAP[status_norm]
    if status_norm not in ALLOWED_STATUSES:
        raise ValueError(f"invalid status: {status}")

    # normalize components
    normalized: Dict[str, Dict[str, Any]] = {}
    for name, info in components.items():
        comp_status = info.get("status") if isinstance(info, dict) else None
        comp_details = info.get("details") if isinstance(info, dict) else {}
        # normalize component status (case-insensitive, alias-aware)
        comp_status_norm = (comp_status or "").lower()
        if comp_status_norm in ALIAS_MAP:
            comp_status_norm = ALIAS_MAP[comp_status_norm]
        if not comp_status_norm or comp_status_norm not in ALLOWED_STATUSES:
            raise ValueError(f"invalid component status for {name}: {comp_status}")
        normalized[name] = {"status": comp_status_norm, "details": comp_details}

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
    # normalize and validate status (accept alias like 'warn')
    status = obj.get("status")
    status_norm = (status or "").lower()
    if status_norm in ALIAS_MAP:
        status_norm = ALIAS_MAP[status_norm]
    if status_norm not in ALLOWED_STATUSES:
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
            comp_status_norm = (comp_status or "").lower()
            if comp_status_norm in ALIAS_MAP:
                comp_status_norm = ALIAS_MAP[comp_status_norm]
            if comp_status_norm not in ALLOWED_STATUSES:
                errors.append(f"component {name} has invalid status: {comp_status}")

    return (len(errors) == 0, errors)


def sample_health_ok(version: Optional[str] = None) -> Dict[str, Any]:
    """Helper that returns a minimal 'ok' health object for tests and smoke checks."""
    components = {"api": {"status": "ok", "details": {}}}
    uptime = int(time.time() - STARTUP_AT) if "STARTUP_AT" in globals() else 0
    return make_health("ok", uptime, components, version=version)


# Optional module-level startup timestamp used in sample helpers during tests
STARTUP_AT = time.time()


# ------------------------------------------------------------------
# Runtime health helpers (Python equivalents of lib/health-common.sh)
# ------------------------------------------------------------------


def _http_get(url: str, timeout: int = 5) -> Optional[str]:
    """Tiny HTTP GET helper: uses requests if available, else urllib."""
    try:
        if requests:
            r = requests.get(url, timeout=timeout)
            if r.status_code in (200, 204, 301, 302):
                return r.text
            return None
        # fallback to urllib
        from urllib.request import urlopen

        with urlopen(url, timeout=timeout) as fh:
            return fh.read().decode("utf-8")
    except Exception:
        return None


def log_info(component: str, msg: str) -> None:
    try:
        from .log_utils import log_info as _log_info

        _log_info(component, msg)
    except Exception:
        # best-effort fallback
        print(f"INFO [{component}] {msg}")


def log_warn(component: str, msg: str) -> None:
    try:
        from .log_utils import log_warn as _log_warn

        _log_warn(component, msg)
    except Exception:
        print(f"WARN [{component}] {msg}")


def log_error(component: str, msg: str) -> None:
    try:
        from .log_utils import log_error as _log_error

        _log_error(component, msg)
    except Exception:
        print(f"ERROR [{component}] {msg}")


def check_client_process(process_name: str = "vpn-sentinel-client") -> str:
    """Return 'healthy' if process is running, 'not_running' otherwise.

    Searches for both Python (.py) and shell (.sh) client processes.
    Tries psutil first, then falls back to `pgrep -f` on POSIX systems.
    """
    # Support both Python and shell client scripts
    search_patterns = [
        "vpn-sentinel-client.py",
        "vpn-sentinel-client.sh",
        process_name  # Custom pattern if provided
    ]
    
    try:
        if psutil:
            for p in psutil.process_iter(attrs=["cmdline", "name"]):
                try:
                    cmd = " ".join(p.info.get("cmdline") or [])
                except Exception:
                    cmd = ""
                # Check if any of the patterns match
                for pattern in search_patterns:
                    if pattern in cmd or pattern == p.info.get("name"):
                        return "healthy"
        
        # fallback to pgrep - check each pattern
        for pattern in search_patterns:
            res = subprocess.run(
                ["pgrep", "-f", pattern], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            if res.returncode == 0:
                return "healthy"
    except Exception:
        pass
    return "not_running"


def check_network_connectivity(timeout: int = 5) -> str:
    """Check external connectivity using Cloudflare endpoint.

    Returns 'healthy' or 'unreachable'.
    """
    url = "https://1.1.1.1/cdn-cgi/trace"
    body = _http_get(url, timeout=timeout)
    return "healthy" if body else "unreachable"


def check_server_connectivity(server_url: Optional[str] = None, timeout: int = 10) -> str:
    """Check connectivity to the configured VPN Sentinel server.

    Returns 'not_configured' if no server URL provided, 'healthy' or 'unreachable'.
    """
    server = server_url or os.getenv("VPN_SENTINEL_URL", "")
    if not server:
        return "not_configured"
    # Perform a simple HEAD/GET to determine reachability
    try:
        # prefer HEAD if requests is available
        if requests:
            r = requests.head(server, timeout=timeout)
            if r.status_code >= 200 and r.status_code < 400:
                return "healthy"
            # try GET as a fallback
            r = requests.get(server, timeout=timeout)
            return "healthy" if r.status_code < 400 else "unreachable"
        # urllib fallback: do a GET
        body = _http_get(server, timeout=timeout)
        return "healthy" if body is not None else "unreachable"
    except Exception:
        return "unreachable"


def check_dns_leak_detection(timeout: int = 5) -> str:
    """Basic check for DNS lookup availability (uses ipinfo.io)."""
    url = "https://ipinfo.io/json"
    body = _http_get(url, timeout=timeout)
    return "healthy" if body else "unavailable"


def get_system_info() -> Dict[str, str]:
    """Return a small dict with memory_percent and disk_percent (strings).

    Tries psutil if available, otherwise falls back to `free`/`df` parsing.
    """
    memory_percent = "unknown"
    disk_percent = "unknown"
    try:
        if psutil:
            mem = psutil.virtual_memory()
            memory_percent = f"{mem.percent:.1f}"
        else:
            # try parsing /proc/meminfo
            if os.path.exists("/proc/meminfo"):
                with open("/proc/meminfo") as fh:
                    data = fh.read()
                # best-effort: not exact but ok for small utility
                lines = {l.split(":")[0]: l.split(":")[1].strip() for l in data.splitlines() if ":" in l}
                mem_total = int(lines.get("MemTotal", "0 kB").split()[0])
                mem_free = int(lines.get("MemFree", "0 kB").split()[0])
                if mem_total > 0:
                    used = mem_total - mem_free
                    memory_percent = f"{(used / mem_total) * 100:.1f}"
        # disk usage for /
        if psutil:
            disk = psutil.disk_usage("/")
            disk_percent = f"{disk.percent:.1f}"
        else:
            # fallback to df
            try:
                out = subprocess.check_output(["df", "/", "--output=pcent"], text=True)
                # skip header line
                lines = out.strip().splitlines()
                if len(lines) >= 2:
                    val = lines[1].strip().strip("%")
                    disk_percent = val
            except Exception:
                pass
    except Exception:
        pass

    return {"memory_percent": str(memory_percent), "disk_percent": str(disk_percent)}
