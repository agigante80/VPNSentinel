import json
import os
import subprocess
import sys


def shim_path():
    # Point at the canonical client shim (repaired file)
    return os.path.normpath(os.path.join(os.path.dirname(__file__), "../../vpn_sentinel_common/health_scripts/health_common_shim.py"))


def run_shim(args):
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.normpath(os.path.join(os.path.dirname(__file__), "../.."))
    cmd = [sys.executable, shim_path()] + args
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def test_get_system_info_json():
    rc, out, err = run_shim(["get_system_info", "--json"])
    assert rc == 0
    # Should be valid JSON with memory_percent and disk_percent
    data = json.loads(out)
    assert "memory_percent" in data
    assert "disk_percent" in data


def test_check_client_process_and_network():
    rc1, out1, err1 = run_shim(["check_client_process"])
    rc2, out2, err2 = run_shim(["check_network_connectivity"])

    # Outputs should be non-empty strings (healthy, not_running, unreachable, etc.)
    assert rc1 == 0 or rc1 == 1
    assert isinstance(out1, str) and out1 != ""

    assert rc2 == 0 or rc2 == 1
    assert isinstance(out2, str) and out2 != ""


def test_generate_health_status_json():
    rc, out, err = run_shim(["generate_health_status"])
    assert rc == 0
    data = json.loads(out)
    assert "status" in data
    assert "checks" in data and isinstance(data["checks"], dict)
