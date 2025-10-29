# Server-dependent integration tests

These tests exercise the VPN Sentinel server and require a running server (or Docker compose) and any required credentials. They are intentionally separated from the client-focused `tests/integration/` suite and are skipped by default to avoid accidental execution in CI.

How to run
---------

Enable the integration_server suite explicitly and run pytest:

```bash
export VPN_SENTINEL_SERVER_TESTS=1
# Optionally set the server URL and API path
export VPN_SENTINEL_URL=http://localhost:5000
export VPN_SENTINEL_API_PATH=/api/v1
# If the server expects an API key
export VPN_SENTINEL_API_KEY=your_test_api_key

pytest -q tests/integration_server
```

Notes and requirements
----------------------

- These tests may start services (Flask apps) or rely on Docker Compose.
- If a test requires Docker Compose, ensure `docker-compose` is installed and available in PATH.
- Some tests require specific ports to be available (default: 5000 for API, 8081 for health). You can override ports via the environment variables listed in each test file.
- Tests are intentionally skipped by default. Do not remove the `pytest.skip(...)` shims in `tests/integration/` unless you intend to re-enable them.

Recommended workflow
--------------------

1. Build server and client images if you plan to run the full stack locally (optional):

   ```bash
   # from repo root
   docker build -t vpn-sentinel-server:local vpn-sentinel-server/
   docker build -t vpn-sentinel-client:local vpn-sentinel-client/
   ```

2. Start server with Docker Compose (if you prefer):

   ```bash
   docker compose up -d
   ```

3. Run the test suite in this folder after setting the environment variables above.

CI recommendation
-----------------

Keep these tests out of the default CI test matrix. Add an opt-in job that runs `pytest tests/integration_server` only when a pipeline variable (for example `run_server_tests=true`) is set.

Troubleshooting
---------------

- If a test is skipped with a message about the server not running, verify the server URL, ports, and API key environment variables.
- Check `docker compose logs` if using Docker Compose to start the server.

If you want, I can add a small CI workflow snippet that runs these tests only when explicitly requested.
