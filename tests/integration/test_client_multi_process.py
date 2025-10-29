"""Moved to tests/integration_server/ (server-dependent).

This file is a harmless shim so the client-focused `tests/integration/` suite
does not accidentally run heavy, server-dependent tests. To run the real
tests, enable the integration server suite:

    export VPN_SENTINEL_SERVER_TESTS=1
    pytest tests/integration_server -q

"""

import pytest

pytest.skip("Moved to tests/integration_server/ (server-dependent). Set VPN_SENTINEL_SERVER_TESTS=1 to run.", allow_module_level=True)