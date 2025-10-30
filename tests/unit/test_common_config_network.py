import json
from vpn_sentinel_common import config as common_config
from vpn_sentinel_common import network as common_network


def test_generate_client_id_from_env():
    env = {"VPN_SENTINEL_CLIENT_ID": "My_Client!"}
    cid = common_config.generate_client_id(env)
    assert "my-client" in cid or cid.startswith("vpn-client-")


def test_load_config_defaults():
    env = {}
    cfg = common_config.load_config(env)
    assert isinstance(cfg, dict)
    assert "server_url" in cfg


def test_parse_geolocation_ipinfo():
    text = json.dumps({"ip": "1.2.3.4", "country": "US", "city": "X"})
    out = common_network.parse_geolocation(text)
    assert out["ip"] == "1.2.3.4"


def test_parse_dns_trace():
    trace = "loc=NYC\ncolo=nyc1\n"
    out = common_network.parse_dns_trace(trace)
    assert out["loc"] == "NYC"
    assert out["colo"] == "nyc1"
