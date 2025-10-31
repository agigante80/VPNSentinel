import json
import subprocess
import sys
from pathlib import Path

from vpn_sentinel_common import health as vs_health


def test_health_helpers_return_expected_statuses():
    # Call the canonical health helpers directly (no compatibility wrapper)
    client_status = vs_health.check_client_process()
    network_status = vs_health.check_network_connectivity()

    assert isinstance(client_status, str)
    assert client_status in ("healthy", "not_running")

    assert isinstance(network_status, str)
    assert network_status in ("healthy", "unreachable")


def test_health_shim_cli_outputs_json():
    # Point at the canonical shim under the repository root (not the old tests wrapper)
    script = Path(__file__).resolve().parents[2] / 'vpn-sentinel-client' / 'lib' / 'health.py'
    assert script.exists(), f"Could not find {script}"
    p = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    assert p.returncode == 0
    out = p.stdout.strip()
    data = json.loads(out)
    assert isinstance(data, dict)
    # Expect some keys to be present (falls back to defaults if canonical lib not installed)
    assert 'client_process' in data
    assert 'network_connectivity' in data
