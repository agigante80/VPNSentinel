"""Prometheus metrics for the health app (GET /metrics).

State is read at scrape time by a custom collector in a PRIVATE registry (never the process-global
default registry, so test re-imports cannot raise duplicate-registration errors). Labels are limited
to client_id and status: no IP address or geolocation is ever exported.
"""

import ipaddress
import os
import sys
import threading
import time
from datetime import datetime, timezone

from prometheus_client import CollectorRegistry
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.exposition import CONTENT_TYPE_PLAIN_0_0_4, generate_latest

from . import api_routes
from .client_health import classify_client
from .config import read_secret
from .log_utils import log_error, log_warn

STATUS_VALUES = {"green": 0, "yellow": 1, "red": 2}
CONTENT_TYPE = CONTENT_TYPE_PLAIN_0_0_4

# Optional bearer token for /metrics, read ONCE at import (from VPN_SENTINEL_METRICS_TOKEN or
# VPN_SENTINEL_METRICS_TOKEN_FILE). Empty means /metrics is public. A bad file is fatal, so a broken
# token file can never silently result in an open endpoint.
try:
    METRICS_TOKEN = read_secret("VPN_SENTINEL_METRICS_TOKEN")
except ValueError as _secret_err:
    log_error("config", str(_secret_err))
    sys.exit(1)

AUTH_LOG_WINDOW_SECONDS = 60
_auth_log_lock = threading.Lock()
_auth_suppressed = 0
_auth_window_start = None


def reset_auth_failure_throttle():
    """Forget the failed-attempt log window (test isolation)."""
    global _auth_suppressed, _auth_window_start
    with _auth_log_lock:
        _auth_suppressed = 0
        _auth_window_start = None


def log_auth_failure(remote_addr):
    """Log a failed /metrics auth at most once per window; later failures only bump a counter.

    The window is global, not per IP: during a burst only the first caller's address is logged
    and the rest are counted without one. That bounds log volume with no per-IP state to grow.
    The address is the socket address, never X-Forwarded-For (caller controlled). Neither the
    configured token nor the presented credential is ever logged.
    """
    global _auth_suppressed, _auth_window_start
    now = time.monotonic()
    with _auth_log_lock:
        if _auth_window_start is not None and now - _auth_window_start < AUTH_LOG_WINDOW_SECONDS:
            _auth_suppressed += 1
            return
        suppressed = _auth_suppressed
        _auth_suppressed = 0
        _auth_window_start = now
    suffix = f" ({suppressed} more suppressed)" if suppressed else ""
    log_warn("security", f"metrics auth failed | IP: {remote_addr}{suffix}")


def metrics_enabled():
    """Read per request (unlike the dashboard toggle, which is read at startup) so it can be flipped live."""
    return os.getenv("VPN_SENTINEL_METRICS_ENABLED", "true").strip().lower() not in ("false", "0", "no", "off")


def _is_real_address(value):
    """A "real address" is any value ipaddress.ip_address() accepts (so None, "", "Unknown" are not)."""
    if not isinstance(value, str):
        return False
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True


def _parse_timestamp(value):
    """Unix time from a stored ISO string (naive values are taken as UTC), or None if unparseable."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _build_families(snapshot, server_ip):
    """Build metric families from a copy of client_status. Runs WITHOUT client_status_lock held."""
    known = _is_real_address(server_ip)

    counts = {status: 0 for status in STATUS_VALUES}
    status_family = GaugeMetricFamily(
        "vpn_sentinel_client_status", "Client status: 0 green, 1 yellow, 2 red", labels=["client_id"]
    )
    ts_family = GaugeMetricFamily(
        "vpn_sentinel_client_last_keepalive_timestamp_seconds",
        "Unix time of the client's last keepalive",
        labels=["client_id"],
    )

    for client_id, client in snapshot.items():
        ts = _parse_timestamp(client.get("last_seen"))
        if ts is not None:
            ts_family.add_metric([client_id], ts)
        # Red needs the server IP to be judged (a bypassing client would otherwise compare unequal and look
        # green), so no status is emitted while it is unknown, even for clients with a stored ip of "unknown".
        # The dashboard behaves the same way; alert on vpn_sentinel_server_ip_known == 0 for the blind spot.
        if known:
            status = classify_client(client, server_ip)
            counts[status] += 1
            status_family.add_metric([client_id], STATUS_VALUES[status])

    clients_family = GaugeMetricFamily("vpn_sentinel_clients", "Clients per status", labels=["status"])
    for status in STATUS_VALUES:
        clients_family.add_metric([status], counts[status])

    known_family = GaugeMetricFamily(
        "vpn_sentinel_server_ip_known", "1 when the cached server public IP is a real address", value=1 if known else 0
    )
    up_family = GaugeMetricFamily("vpn_sentinel_up", "VPN Sentinel server is up", value=1)
    return [up_family, known_family, clients_family, status_family, ts_family]


class ClientStatusCollector:
    """Custom collector: snapshots client_status under the lock, then builds families outside it."""

    def collect(self):
        with api_routes.client_status_lock:
            snapshot = {cid: dict(c) for cid, c in api_routes.client_status.items()}
        # Cache only: a scrape must never start the (up to ~20 s) outbound server IP lookup.
        # The dashboard reads get_server_info() instead of this cache, so the two can disagree on the server IP.
        server_ip = api_routes.peek_cached_server_ip()
        return _build_families(snapshot, server_ip)


def build_registry():
    registry = CollectorRegistry(auto_describe=False)
    registry.register(ClientStatusCollector())
    return registry


def render_metrics():
    return generate_latest(build_registry())
