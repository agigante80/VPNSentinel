"""Legacy health integration tests moved to tests/integration_server.

These tests start server processes and/or require Docker. They have been
moved to `tests/integration_server/` and are skipped by default. This shim is
kept so test discovery in `tests/integration/` remains fast and safe.
"""
import pytest

pytest.skip("Moved to tests/integration_server/ (server-dependent). Set VPN_SENTINEL_SERVER_TESTS=1 to run.", allow_module_level=True)