import json
import os
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
    script = Path(__file__).resolve().parents[2] / 'vpn_sentinel_common' / 'health_scripts' / 'healthcheck.py'
    assert script.exists(), f"Could not find {script}"
    env = os.environ.copy()
    env['PYTHONPATH'] = str(Path(__file__).resolve().parents[2])
    p = subprocess.run([sys.executable, str(script), '--json'], capture_output=True, text=True, env=env)
    out = p.stdout.strip()
    # Find the JSON part (it comes after the human-readable output)
    lines = out.split('\n')
    json_start = None
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith('{'):
            json_start = i
            break
    assert json_start is not None, f"Could not find JSON start in: {out}"
    json_text = '\n'.join(lines[json_start:])
    data = json.loads(json_text)
    assert isinstance(data, dict)
    # Expect some keys to be present (falls back to defaults if canonical lib not installed)
    assert 'checks' in data
    checks = data['checks']
    assert 'client_process' in checks
    assert 'network_connectivity' in checks
