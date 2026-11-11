"""Health server routes for VPN Sentinel."""

from .server import health_app
from flask import Response, abort, jsonify

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


@health_app.route("/metrics", methods=["GET"])
def prometheus_metrics():
    """Prometheus exposition. Public like /health; carries client IDs, never IPs or geolocation."""
    if not metrics.metrics_enabled():
        abort(404)
    return Response(metrics.render_metrics(), content_type=metrics.CONTENT_TYPE)
