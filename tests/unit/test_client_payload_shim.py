import json
import os
import sys
from pathlib import Path
from subprocess import Popen, PIPE


def _get_payload_script_path():
    # tests are under tests/unit; repo root is two parents up from this file
    # Legacy tests used to exec the payload shim path. For migration we call the
    # canonical package directly.
    return None


def test_build_payload_prints_valid_json(monkeypatch):
    # Ensure environment variables produce predictable output
    monkeypatch.setenv("CLIENT_ID", "test-client")
    monkeypatch.setenv("PUBLIC_IP", "1.2.3.4")
    monkeypatch.setenv("COUNTRY", "US")
    # Call canonical implementation directly
    from vpn_sentinel_common.payload import build_payload_from_env
    data = build_payload_from_env()
    assert data["client_id"] == "test-client"
    assert data["public_ip"] == "1.2.3.4"


def test_post_payload_writes_capture_file(tmp_path, monkeypatch):
    cap = tmp_path / "capture.log"
    # Ensure the canonical post implementation writes to our capture path
    monkeypatch.setenv("VPN_SENTINEL_TEST_CAPTURE_PATH", str(cap))
    # Build a simple payload and post via canonical functions
    from vpn_sentinel_common.payload import build_payload_from_env, post_payload
    ptxt = json.dumps(build_payload_from_env())
    rc = post_payload(ptxt)
    assert rc == 0
    assert cap.exists()
    # capture file should contain a single-line JSON
    line = cap.read_text(encoding="utf-8").strip()
    assert line.startswith("{") and line.endswith("}")
