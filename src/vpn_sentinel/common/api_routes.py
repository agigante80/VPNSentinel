"""API server routes for VPN Sentinel."""

import threading

from .server import api_app
from .log_utils import log_info, log_warn, log_error
from . import telegram
from .server_info import get_server_public_ip
from .validation import get_client_ip, validate_client_id, validate_public_ip, validate_location_string
from .security import check_rate_limit, check_ip_whitelist, ALLOWED_IPS
from flask import jsonify, request
import os

# In-memory storage for client status (in production this would be a database)
client_status = {}
client_status_lock = threading.Lock()

# Get API key from environment (required for authentication)
API_KEY = os.getenv("VPN_SENTINEL_API_KEY", "")

# Load IP whitelist from environment (comma-separated list)
_allowed_ips_env = os.getenv("VPN_SENTINEL_SERVER_ALLOWED_IPS", "")
if _allowed_ips_env:
    ALLOWED_IPS.clear()
    ALLOWED_IPS.extend([ip.strip() for ip in _allowed_ips_env.split(",") if ip.strip()])

# Track if clients have ever connected (to avoid spam on first connect)
_client_first_seen = set()

# Latch for the fleet-empty ("no clients connected") alert: True means the alert has
# already been sent for the current empty state and must not repeat until a client
# registers again. Starts True: on a fresh server start client_status is empty, but no
# client has ever been seen, so a "no clients connected" alert would be spurious. Reads
# and writes of this latch are protected by client_status_lock (shared with the Flask
# keepalive handler and the cleanup thread).
_fleet_empty_reported = True

# Cache server's public IP (fetched once at startup)
_server_public_ip = None

# Client timeout configuration (minutes)
CLIENT_TIMEOUT_MINUTES = int(os.getenv("VPN_SENTINEL_CLIENT_TIMEOUT_MINUTES", "30"))


def get_cached_server_ip():
    """Get server's public IP (cached)."""
    global _server_public_ip
    if _server_public_ip is None:
        _server_public_ip = get_server_public_ip()
    return _server_public_ip


# Get API path from environment
API_PATH = os.getenv("VPN_SENTINEL_API_PATH", "/api/v1").strip("/")
if not API_PATH.startswith("/"):
    API_PATH = "/" + API_PATH

print(f"DEBUG: API_PATH = {API_PATH}")


@api_app.before_request
def authenticate_request():
    """Authenticate API requests using X-API-Key header.

    Security checks applied:
    1. IP whitelist (if configured)
    2. Rate limiting (30 requests/minute per IP)
    3. API key validation

    All API endpoints require authentication except:
    - Health endpoints (handled by separate health_app)
    - Dashboard endpoints (handled by separate dashboard_app)
    """
    client_ip = get_client_ip()

    # 1. Check IP whitelist (if configured)
    if not check_ip_whitelist(client_ip):
        log_error("security", f"❌ IP blocked: {client_ip} not in whitelist | Path: {request.path}")
        return jsonify({"error": "Access denied", "message": "Your IP address is not authorized"}), 403

    # 2. Check rate limiting
    if not check_rate_limit(client_ip):
        log_warn("security", f"⚠️ Rate limit exceeded | IP: {client_ip} | Path: {request.path}")
        return jsonify({"error": "Rate limit exceeded", "message": "Too many requests. Please try again later."}), 429

    # 3. Check API key authentication
    # Skip authentication if no API key is configured (development mode only)
    if not API_KEY:
        log_warn("security", "⚠️ API_KEY not configured - authentication disabled (INSECURE!)")
        return None

    # Get API key from request headers
    provided_key = request.headers.get("X-API-Key", "")

    # Validate API key
    if not provided_key:
        log_error("security", f"❌ Authentication failed: No API key provided | IP: {client_ip} | Path: {request.path}")
        return jsonify({"error": "Authentication required", "message": "X-API-Key header is required"}), 401

    if provided_key != API_KEY:
        log_error("security", f"❌ Authentication failed: Invalid API key | IP: {client_ip} | Path: {request.path}")
        return jsonify({"error": "Authentication failed", "message": "Invalid API key"}), 403

    # All security checks passed
    log_info("security", f"✅ Authenticated request | IP: {client_ip} | Path: {request.path}")
    return None


@api_app.route(f"{API_PATH}/status", methods=["GET"])
def get_status():
    """Get status of all connected clients."""
    with client_status_lock:
        snapshot = dict(client_status)
    return jsonify(snapshot)


@api_app.route(f"{API_PATH}/keepalive", methods=["POST"])
def keepalive():
    """Receive keepalive from a client."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        # Validate and sanitize client_id
        client_id_raw = data.get("client_id")
        if not client_id_raw:
            return jsonify({"error": "client_id is required"}), 400

        client_id = validate_client_id(client_id_raw)
        if client_id == "unknown":
            return jsonify({"error": "Invalid client_id format"}), 400

        # Extract and validate client info (handle both flat and nested formats)
        from datetime import datetime, timezone

        vpn_ip_raw = data.get("public_ip") or data.get("ip", "unknown")
        vpn_ip = validate_public_ip(vpn_ip_raw)

        # Extract and validate location (nested or flat)
        location = data.get("location")
        if location and isinstance(location, dict) and "country" in location:
            # Nested format
            country = validate_location_string(location.get("country", "unknown"), "country")
            city = validate_location_string(location.get("city", "unknown"), "city")
            region = validate_location_string(location.get("region", "unknown"), "region")
            provider = validate_location_string(location.get("org", "unknown"), "provider")
            timezone_str = validate_location_string(location.get("timezone", "unknown"), "timezone")
        else:
            # Flat format
            country = validate_location_string(data.get("country", "unknown"), "country")
            city = validate_location_string(data.get("city", "unknown"), "city")
            region = validate_location_string(data.get("region", "unknown"), "region")
            provider = validate_location_string(data.get("provider", "unknown"), "provider")
            timezone_str = validate_location_string(data.get("timezone", "unknown"), "timezone")

        # Extract and validate DNS test (nested or flat)
        dns_test = data.get("dns_test")
        if dns_test and isinstance(dns_test, dict) and "location" in dns_test:
            # Nested format
            dns_loc = validate_location_string(dns_test.get("location", "Unknown"), "dns_loc")
            dns_colo = validate_location_string(dns_test.get("colo", "Unknown"), "dns_colo")
        else:
            # Flat format
            dns_loc = validate_location_string(data.get("dns_loc", "Unknown"), "dns_loc")
            dns_colo = validate_location_string(data.get("dns_colo", "Unknown"), "dns_colo")

        # Extract client version (optional field)
        client_version = validate_location_string(data.get("client_version", "Unknown"), "version")

        # Read old IP, membership in _client_first_seen, and write new record all under the
        # same lock (avoids the check-then-act race between this handler and the cleanup
        # thread); release the lock before any network I/O.
        global _fleet_empty_reported
        with client_status_lock:
            is_new_client = client_id not in _client_first_seen
            old_ip = client_status.get(client_id, {}).get("ip", None) if not is_new_client else None
            client_status[client_id] = {
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "ip": vpn_ip,
                "location": f"{city}, {region}, {country}",
                "provider": provider,
                "country": country,
                "city": city,
                "region": region,
                "timezone": timezone_str,
                "dns_loc": dns_loc,
                "dns_colo": dns_colo,
                "client_version": client_version,
            }
            if is_new_client:
                _client_first_seen.add(client_id)
            # A client just registered, so the fleet is no longer empty. Clear the latch
            # so the next genuine transition to zero clients can alert again.
            _fleet_empty_reported = False
        ip_changed = old_ip and old_ip != vpn_ip

        # Get server IP for comparison (network call — outside the lock)
        server_ip = get_cached_server_ip()

        # Log keepalive with VPN info
        log_info("api", f"✅ Keepalive from {client_id}")
        log_info("vpn-info", f"  📍 {city}, {country} | 🌐 {vpn_ip} | 🏢 {provider}")

        # Check for VPN bypass
        if vpn_ip == server_ip or vpn_ip == "unknown":
            log_warn("security", f"⚠️ VPN BYPASS WARNING: Client {client_id} has same IP as server ({vpn_ip})")

        # Send Telegram notifications (membership in _client_first_seen was already
        # updated above, under client_status_lock)
        if is_new_client:
            telegram.notify_client_connected(
                client_id,
                vpn_ip,
                f"{city}, {region}, {country}",
                city,
                region,
                country,
                provider,
                timezone_str,
                dns_loc,
                dns_colo,
                server_ip,
                client_version,
            )
        elif ip_changed:
            telegram.notify_ip_changed(
                client_id,
                old_ip,
                vpn_ip,
                city,
                region,
                country,
                provider,
                timezone_str,
                dns_loc,
                dns_colo,
                server_ip,
                client_version,
            )

        return jsonify(
            {"status": "ok", "message": "Keepalive received", "server_time": datetime.now(timezone.utc).isoformat()}
        )

    except Exception as e:
        log_info("api", f"Error processing keepalive: {e}")
        return jsonify({"error": "Internal server error"}), 500


def _run_cleanup_sweep():
    """Run one stale-client sweep: fleet-empty check, staleness detection, removal, alerts.

    Split out of cleanup_stale_clients() so it can be exercised directly in tests without
    driving the surrounding infinite loop/sleep.

    Order of operations, and why:
    1. Check (and possibly latch) the fleet-empty state FIRST, before any early exit. The
       previous implementation bailed out with `if not client_status: continue` before ever
       reaching a zero-clients check, which made notify_no_clients() unreachable whenever the
       dict was already empty -- exactly the state it exists to report. Checking first makes
       that state reachable, at the cost of a check that is a no-op group when the fleet is
       non-empty.
    2. Only after that does it snapshot and evaluate staleness, remove stale clients, and send
       ONE batched Telegram alert for everything removed in this sweep (not one per client),
       since telegram.py has no rate limiting of its own.
    """
    global _fleet_empty_reported
    from datetime import datetime, timezone, timedelta

    # Step 1: fleet-empty latch check. Reachable even when client_status is empty.
    with client_status_lock:
        fleet_is_empty = not client_status
        fire_empty_alert = fleet_is_empty and not _fleet_empty_reported
        if fire_empty_alert:
            _fleet_empty_reported = True
        items_snapshot = [] if fleet_is_empty else list(client_status.items())

    # Send the alert outside the lock (network I/O).
    if fire_empty_alert:
        telegram.notify_no_clients()

    if fleet_is_empty:
        return

    # Step 2: staleness detection (no lock needed; items_snapshot is a private copy).
    current_time = datetime.now(timezone.utc)
    timeout_delta = timedelta(minutes=CLIENT_TIMEOUT_MINUTES)
    stale_clients = []

    for client_id, client_data in items_snapshot:
        last_seen_str = client_data.get("last_seen")
        if not last_seen_str:
            continue

        try:
            # Parse ISO format timestamp
            last_seen = datetime.fromisoformat(last_seen_str.replace("Z", "+00:00"))

            # Ensure timezone-aware
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)

            # Convert to UTC if not already
            if last_seen.tzinfo != timezone.utc:
                last_seen = last_seen.astimezone(timezone.utc)

            # Check if client is stale
            time_since_last_seen = current_time - last_seen
            if time_since_last_seen > timeout_delta:
                stale_clients.append((client_id, time_since_last_seen))

        except (ValueError, AttributeError) as e:
            log_error("cleanup", f"Error parsing last_seen for {client_id}: {e}")
            continue

    # Remove stale clients, collecting everything removed in this sweep for one alert.
    removed = []
    for client_id, time_since_last_seen in stale_clients:
        minutes_ago = int(time_since_last_seen.total_seconds() / 60)
        log_info("cleanup", f"🗑️ Removing stale client: {client_id} (last seen {minutes_ago} minutes ago)")

        # Remove from client status and tracking sets together, under the lock, to avoid
        # racing the keepalive handler's check-then-act on _client_first_seen.
        with client_status_lock:
            if client_id in client_status:
                del client_status[client_id]
            _client_first_seen.discard(client_id)

        removed.append((client_id, minutes_ago))

    # One batched alert for the whole sweep, never one message per client.
    if removed:
        telegram.notify_clients_silent(removed)


def cleanup_stale_clients():
    """Remove clients that haven't sent a keepalive within the timeout period.

    This function runs in a background thread and periodically checks for stale clients.
    Clients are considered stale if they haven't sent a keepalive within CLIENT_TIMEOUT_MINUTES.
    """
    import time

    log_info("cleanup", f"🧹 Starting stale client cleanup thread (timeout: {CLIENT_TIMEOUT_MINUTES} minutes)")

    # Check every 60 seconds
    check_interval = 60

    while True:
        try:
            time.sleep(check_interval)
            _run_cleanup_sweep()

        except Exception as e:
            log_error("cleanup", f"Error in cleanup thread: {e}")
            time.sleep(check_interval)
