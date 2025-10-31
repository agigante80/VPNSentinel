from vpn_sentinel_common import health as vs_health


def test_health_helpers_return_expected_statuses():
    # Call the canonical health helpers directly (no compatibility wrapper)
    client_status = vs_health.check_client_process()
    network_status = vs_health.check_network_connectivity()

    assert isinstance(client_status, str)
    assert client_status in ("healthy", "not_running")

    assert isinstance(network_status, str)
    assert network_status in ("healthy", "unreachable")
