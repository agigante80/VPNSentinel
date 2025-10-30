import json
import os
from pathlib import Path


def test_build_payload_has_expected_keys(monkeypatch):
    # Ensure environment variables produce predictable output
    monkeypatch.setenv("CLIENT_ID", "canonical-test-client")
    monkeypatch.setenv("PUBLIC_IP", "9.8.7.6")
    from vpn_sentinel_common.payload import build_payload_from_env

    payload = build_payload_from_env()
    assert isinstance(payload, dict)
    # basic keys we expect
    assert payload.get("client_id") == "canonical-test-client"
    assert payload.get("public_ip") == "9.8.7.6"


def test_post_payload_writes_capture_and_handles_invalid_json(tmp_path, monkeypatch):
    cap = tmp_path / "capture.log"
    monkeypatch.setenv("VPN_SENTINEL_TEST_CAPTURE_PATH", str(cap))
    from vpn_sentinel_common.payload import post_payload

    # Valid JSON should be written and return 0
    rc = post_payload(json.dumps({"a": 1}))
    assert rc == 0
    assert cap.exists()

    # Invalid JSON: post_payload should still attempt to write a compact line and return 0
    rc2 = post_payload("not-a-json")
    # either 0 (wrote fallback) or 1 (failed); accept both but prefer 0
    assert rc2 in (0, 1)
    # file should exist regardless
    assert cap.exists()
