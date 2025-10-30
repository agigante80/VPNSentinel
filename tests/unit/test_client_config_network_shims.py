import importlib.util
import json
import pathlib


def _load_module_from(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    return mod


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
cfg = _load_module_from(str(REPO_ROOT / "vpn-sentinel-client" / "lib" / "config.py"), "client_config")
net = _load_module_from(str(REPO_ROOT / "vpn-sentinel-client" / "lib" / "network.py"), "client_network")


def test_config_load_defaults():
    env = {}
    c = cfg.load_config(env)
    assert c["api_path"].startswith("/")
    assert isinstance(c["timeout"], int)


def test_parse_geolocation_ipinfo():
    sample = json.dumps({"ip": "1.2.3.4", "country": "US", "city": "Test", "region": "R", "org": "ISP", "timezone": "UTC"})
    parsed = net.parse_geolocation(sample, source="ipinfo.io")
    assert parsed["ip"] == "1.2.3.4"


def test_parse_geolocation_ipapi():
    sample = json.dumps({"query": "5.6.7.8", "countryCode": "GB", "city": "City", "regionName": "Reg", "isp": "ISP2", "timezone": "UTC"})
    parsed = net.parse_geolocation(sample, source="ip-api.com")
    assert parsed["ip"] == "5.6.7.8"


def test_parse_dns_trace():
    trace = "fl=29\nh=1.1.1.1\nip=1.2.3.4\nts=169\nco=US\nloc=US\ncolo=ABC"
    parsed = net.parse_dns_trace(trace)
    assert parsed["loc"] == "US"
    assert parsed["colo"] == "ABC"
