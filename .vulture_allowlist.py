# vulture allowlist for VPNSentinel — curated dynamic-reference false positives.
# Used by scripts/find-dead-code.sh. Each name here looks unused to vulture but is
# load-bearing (see the dynamic-reference table in .claude/skills/find-dead-code/SKILL.md).
# Add a name here ONLY after confirming it is dynamically referenced; never to hide real dead code.
# Regenerate a fresh baseline with: scripts/find-dead-code.sh --baseline  (then prune).

# Flask route handlers — dispatched by URL path, never called by name (@*_app.route / before_request)
authenticate_request  # api_routes.py — security middleware / before_request
get_status            # api_routes.py — GET /status route
keepalive             # api_routes.py — POST /keepalive route
dashboard_slash       # dashboard_routes.py — /dashboard/ route
server_logs           # dashboard_routes.py — /dashboard logs route
health_ready          # health_routes.py — /health/ready route
health_startup        # health_routes.py — /health/startup route

# Werkzeug/Flask logging integration — methods invoked by the framework, not by name
VPNSentinelLogHandler  # server_utils.py — logging.Handler subclass registered with the app
log_request            # server_utils.py — handler method called by the logging framework

# Signal-handler signature parameters — required by the signal API, intentionally unused
signum  # def handler(signum, frame): ... (client/__main__.py, health_monitor.py, health_scripts/)
frame

# Flexible-signature stub that accepts and ignores positional/keyword args by design
args    # security.py — log_access(*args, **kwargs) compatibility shim
kwargs
size    # server_utils.py — handler arg required by the framework signature

# Public API with test coverage (documented surface; vulture 60% false positive)
validate_health    # health.py: public health-schema validator, used by integration + unit tests
is_running         # monitor.py: documented Monitor API method; Monitor is used in health_monitor.py

# Test-only helpers (no production caller; intentional sample/util functions exercised by tests)
sample_health_ok   # health.py: sample-payload generator for health tests
heartbeat_json     # monitor.py: public Monitor method, exercised only by tests
get_version_info   # version.py: version-info dict helper, exercised only by tests
parse_geolocation  # network.py: public parser used via client shims/tests
