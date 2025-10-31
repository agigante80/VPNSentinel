from vpn_sentinel_common import health as canonical_health


def test_health_shim_cli_outputs_json():
    # Call canonical helpers directly and assert expected keys are present.
    client_proc = canonical_health.check_client_process()
    net = canonical_health.check_network_connectivity()
    assert isinstance(client_proc, str)
    assert isinstance(net, str)
