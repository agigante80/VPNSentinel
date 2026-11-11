"""Health server routes for VPN Sentinel."""

import hmac

from .server import health_app
from flask import Response, abort, jsonify, request

from . import metrics


@health_app.route("/health")
def health():
    """Basic health check endpoint."""
    return jsonify(
        {
            "status": "ok",
            "message": "VPN Sentinel Health Server is running",
            "server_time": "unknown",  # Could add timestamp if needed
        }
    )


@health_app.route("/health/ready")
def health_ready():
    """Readiness health check."""
    return jsonify({"status": "ok", "message": "VPN Sentinel Health Server is ready"})


@health_app.route("/health/startup")
def health_startup():
    """Startup health check."""
    return jsonify({"status": "ok", "message": "VPN Sentinel Health Server started successfully"})


def _metrics_authorized():
    """True when no token is configured or the request carries `Authorization: Bearer <token>`."""
    if not metrics.METRICS_TOKEN:
        return True
    scheme, _, credential = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not credential:
        return False
    return hmac.compare_digest(credential.encode(), metrics.METRICS_TOKEN.encode())


@health_app.route("/metrics", methods=["GET"])
def prometheus_metrics():
    """Prometheus exposition. Public unless VPN_SENTINEL_METRICS_TOKEN is set, then bearer-protected.

    Carries client IDs, never IPs or geolocation. Disabled (404) wins over the token check.
    """
    if not metrics.metrics_enabled():
        abort(404)
    if not _metrics_authorized():
        metrics.log_auth_failure(request.remote_addr)
        return Response(
            "Unauthorized",
            status=401,
            headers={"WWW-Authenticate": 'Bearer realm="vpn-sentinel-metrics"', "Cache-Control": "no-store"},
        )
    return Response(metrics.render_metrics(), content_type=metrics.CONTENT_TYPE)
