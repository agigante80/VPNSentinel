"""get_cached_server_ip retries a failed ("Unknown") lookup, but at most every SERVER_IP_RETRY_SECONDS."""

from unittest.mock import patch

import pytest

from vpn_sentinel.common import api_routes


@pytest.fixture(autouse=True)
def reset_cache():
    api_routes._server_public_ip = None
    api_routes._server_ip_fetched_at = 0.0
    yield
    api_routes._server_public_ip = None
    api_routes._server_ip_fetched_at = 0.0


def test_real_ip_is_fetched_once():
    with (
        patch.object(api_routes, "get_server_public_ip", return_value="203.0.113.9") as lookup,
        patch.object(api_routes.time, "monotonic", side_effect=[1000.0, 99999.0]),
    ):
        assert api_routes.get_cached_server_ip() == "203.0.113.9"
        assert api_routes.get_cached_server_ip() == "203.0.113.9"
    assert lookup.call_count == 1


def test_unknown_is_not_retried_before_the_interval():
    with (
        patch.object(api_routes, "get_server_public_ip", return_value="Unknown") as lookup,
        patch.object(
            api_routes.time, "monotonic", side_effect=[1000.0, 1000.0 + api_routes.SERVER_IP_RETRY_SECONDS - 1]
        ),
    ):
        assert api_routes.get_cached_server_ip() == "Unknown"
        assert api_routes.get_cached_server_ip() == "Unknown"
    assert lookup.call_count == 1


def test_unknown_is_retried_after_the_interval_and_recovers():
    with (
        patch.object(api_routes, "get_server_public_ip", side_effect=["Unknown", "203.0.113.9"]) as lookup,
        patch.object(api_routes.time, "monotonic", side_effect=[1000.0, 1000.0 + api_routes.SERVER_IP_RETRY_SECONDS]),
    ):
        assert api_routes.get_cached_server_ip() == "Unknown"
        assert api_routes.get_cached_server_ip() == "203.0.113.9"
    assert lookup.call_count == 2
    assert api_routes.peek_cached_server_ip() == "203.0.113.9"
