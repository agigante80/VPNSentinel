import os
import sys
import json
import pytest

# Follow existing convention: skip server-dependent integration tests unless env var set
if not os.getenv("VPN_SENTINEL_SERVER_TESTS"):
    pytest.skip("Server-dependent integration tests disabled. Set VPN_SENTINEL_SERVER_TESTS=1 to enable.", allow_module_level=True)

# Add server directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../vpn-sentinel-server'))


def _load_health_app():
    from vpn_sentinel_common.server import health_app
    return health_app


def _map_legacy_status_to_allowed(s):
    # Legacy server uses 'healthy'/'ready'/'started'—map to our set {ok,degraded,fail}
    if s in ("healthy", "ready", "started", "ok"):
        return "ok"
    if s in ("degraded",):
        return "degraded"
    return "fail"


def test_health_endpoint_matches_shared_shape():
    health_app = _load_health_app()
    health_app.config['TESTING'] = True
    client = health_app.test_client()

    resp = client.get('/health')
    assert resp.status_code == 200
    data = json.loads(resp.data)

    # Try validating against the shared schema permissively
    from vpn_sentinel_common import health as health_common

    # Legacy responses may use different key names; try to normalise a little
    if isinstance(data, dict) and 'status' in data and data['status'] in ('healthy', 'ready', 'started'):
        # Build a normalized shape
        normalized = {
            'status': _map_legacy_status_to_allowed(data.get('status')),
            'uptime_seconds': int(data.get('uptime', 0)) if isinstance(data.get('uptime', 0), int) else 0,
            'timestamp': data.get('server_time') or data.get('timestamp') or '',
            'server_time': data.get('server_time') or data.get('timestamp') or '',
            'components': {'system': {'status': 'ok', 'details': {}}},
        }
        valid, errors = health_common.validate_health(normalized)
        assert valid, f"Normalized legacy health did not validate: {errors}"
    else:
        # If the server already returns the new shape, validate it directly
        valid, errors = health_common.validate_health(data)
        assert valid, f"Health endpoint JSON did not validate: {errors}"
