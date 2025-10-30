import json
import subprocess
import sys
from pathlib import Path


def test_health_shim_cli_outputs_json():
    script = Path(__file__).resolve().parents[1] / 'vpn-sentinel-client' / 'lib' / 'health.py'
    assert script.exists(), f"Could not find {script}"
    p = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    assert p.returncode == 0
    out = p.stdout.strip()
    data = json.loads(out)
    assert isinstance(data, dict)
    # Expect some keys to be present (falls back to defaults if canonical lib not installed)
    assert 'client_process' in data
    assert 'network_connectivity' in data
