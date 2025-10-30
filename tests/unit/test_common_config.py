import os
from vpn_sentinel_common.config import load_config, generate_client_id


def test_generate_client_id_from_env():
    env = {"VPN_SENTINEL_CLIENT_ID": "my-client-1"}
    cid = generate_client_id(env)
    assert cid == "my-client-1"


def test_generate_client_id_sanitize():
    env = {"VPN_SENTINEL_CLIENT_ID": "My Client!"}
    cid = generate_client_id(env)
    assert "my-client" in cid


def test_load_config_defaults(monkeypatch):
    env = {}
    cfg = load_config(env)
    assert "server_url" in cfg
    assert cfg["api_path"].startswith("/")


def test_load_config_numeric_parsing(monkeypatch):
    env = {"VPN_SENTINEL_TIMEOUT": "notanumber", "VPN_SENTINEL_INTERVAL": "100"}
    cfg = load_config(env)
    # timeout should fall back to default (30)
    assert isinstance(cfg["timeout"], int)
    assert cfg["interval"] == 100
