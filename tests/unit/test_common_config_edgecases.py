import os
import json
import pytest

from vpn_sentinel_common import config as cfg


def test_api_path_normalization_leading_missing_slash():
    env = {"VPN_SENTINEL_URL": "http://example.local", "VPN_SENTINEL_API_PATH": "api/v2"}
    conf = cfg.load_config(env)
    assert conf["api_path"].startswith("/"), "api_path should be normalized to start with '/'."
    assert conf["server_url"] == "http://example.local/api/v2"


def test_non_int_interval_and_timeout_fallbacks():
    env = {"VPN_SENTINEL_URL": "http://example.local", "VPN_SENTINEL_INTERVAL": "notanint", "VPN_SENTINEL_TIMEOUT": "alsoNaN"}
    # Should not raise; use defaults when non-int provided
    conf = cfg.load_config(env)
    assert isinstance(conf["interval"], int)
    assert isinstance(conf["timeout"], int)
    assert conf["interval"] == 300
    assert conf["timeout"] == 30


def test_client_id_sanitization_special_chars():
    env = {"VPN_SENTINEL_CLIENT_ID": "My$Special:ID!!"}
    cid = cfg.generate_client_id(env)
    assert cid == "my-special-id", f"Sanitized client id expected 'my-special-id', got {cid}"


def test_generate_client_id_from_env_preserves_valid():
    env = {"VPN_SENTINEL_CLIENT_ID": "valid-id-123"}
    cid = cfg.generate_client_id(env)
    assert cid == "valid-id-123"
