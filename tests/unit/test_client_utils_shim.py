import subprocess
import sys
from pathlib import Path


def test_utils_shim_cli_sanitize():
    script = Path(__file__).resolve().parents[1] / 'vpn-sentinel-client' / 'lib' / 'utils.py'
    assert script.exists(), f"Could not find {script}"
    p = subprocess.run([sys.executable, str(script), '--sanitize', 'a\x00b\x1fb'], capture_output=True, text=True)
    assert p.returncode == 0
    assert p.stdout.strip() == 'ab'


def test_utils_shim_cli_escape():
    script = Path(__file__).resolve().parents[1] / 'vpn-sentinel-client' / 'lib' / 'utils.py'
    p = subprocess.run([sys.executable, str(script), '--json-escape', 'a"b\\c'], capture_output=True, text=True)
    assert p.returncode == 0
    assert p.stdout.strip() == 'a\"b\\c'
