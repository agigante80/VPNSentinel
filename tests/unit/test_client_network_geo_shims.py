from vpn_sentinel_common.network import parse_geolocation as common_parse_geolocation, parse_dns_trace as common_parse_dns
import vpn_sentinel_common
import json
import importlib.util
import pathlib


def _load_module_from(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    return mod


client_net = None
from vpn_sentinel_common import network as client_net


def test_client_network_shim_parse_geolocation_ipinfo():
    # sample ipinfo payload
    sample = json.dumps({
        "ip": "1.2.3.4",
        "country": "US",
        "city": "Testville",
        "region": "TestState",
        "org": "TestOrg",
        "timezone": "UTC"
    })

    c = client_net.parse_geolocation(sample, source="ipinfo.io")
    s = common_parse_geolocation(sample, source="ipinfo.io")
    assert c == s


def test_client_network_shim_parse_geolocation_ipapi():
    ipapi = json.dumps({
        "query": "5.6.7.8",
        "countryCode": "GB",
        "city": "London",
        "regionName": "Greater London",
        "isp": "ISP Ltd",
        "timezone": "Europe/London"
    })

    c = client_net.parse_geolocation(ipapi, source="ip-api.com")
    s = common_parse_geolocation(ipapi, source="ip-api.com")
    assert c == s


def test_client_network_shim_parse_dns_trace():
    trace = "loc=EWR1\ncolo=ewr"
    c = client_net.parse_dns_trace(trace)
    s = common_parse_dns(trace)
    assert c == s
