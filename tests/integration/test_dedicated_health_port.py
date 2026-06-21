"""Legacy dedicated health port tests moved to tests/integration/server_dependent.

These tests are server-dependent and have been moved. Keep a shim so
discovery in `tests/integration/` is safe and fast.
"""
import pytest
import unittest

pytest.skip("Moved to tests/integration/server_dependent/ (server-dependent). Set VPN_SENTINEL_SERVER_TESTS=1 to run.", allow_module_level=True)


if __name__ == '__main__':
    unittest.main()