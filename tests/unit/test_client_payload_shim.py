import json
import os
import sys
from pathlib import Path
from subprocess import Popen, PIPE


def _get_payload_script_path():
    # tests are under tests/unit; repo root is two parents up from this file
    return str(Path(__file__).resolve().parents[2] / "vpn-sentinel-client" / "lib" / "payload.py")


def test_build_payload_prints_valid_json(monkeypatch):
    # Ensure environment variables produce predictable output
    monkeypatch.setenv("CLIENT_ID", "test-client")
    monkeypatch.setenv("PUBLIC_IP", "1.2.3.4")
    monkeypatch.setenv("COUNTRY", "US")
    script = _get_payload_script_path()
    p = Popen([sys.executable, script, "--build-json"], stdout=PIPE)
    out, _ = p.communicate()
    data = json.loads(out.decode())
    assert data["client_id"] == "test-client"
    assert data["public_ip"] == "1.2.3.4"


def test_post_payload_writes_capture_file(tmp_path):
    cap = tmp_path / "capture.log"
    env = os.environ.copy()
    env["VPN_SENTINEL_TEST_CAPTURE_PATH"] = str(cap)
    # Build a simple payload and post via shim
    script = _get_payload_script_path()
    p1 = Popen([sys.executable, script, "--build-json"], stdout=PIPE, env=env)
    out, _ = p1.communicate()
    p2 = Popen([sys.executable, script, "--post"], stdin=PIPE, env=env)
    p2.communicate(out)
    assert cap.exists()
    # capture file should contain a single-line JSON
    line = cap.read_text(encoding="utf-8").strip()
    assert line.startswith("{") and line.endswith("}")
