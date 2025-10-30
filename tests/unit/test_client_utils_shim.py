import subprocess
import sys
from pathlib import Path


def test_utils_shim_cli_sanitize():
    script = Path(__file__).resolve().parents[1] / 'vpn-sentinel-client' / 'lib' / 'utils.py'
    assert script.exists(), f"Could not find {script}"
    # Avoid NUL (\x00) in argv — some platforms disallow it. Use 0x1f control
    # character which is safe to pass and still validates stripping of control
    # characters.
    p = subprocess.run([sys.executable, str(script), '--sanitize', 'a\x1fb'], capture_output=True, text=True)
    assert p.returncode == 0
    assert p.stdout.strip() == 'ab'


def test_utils_shim_cli_escape():
    script = Path(__file__).resolve().parents[1] / 'vpn-sentinel-client' / 'lib' / 'utils.py'
    raw = 'a"b\\c'
    p = subprocess.run([sys.executable, str(script), '--json-escape', raw], capture_output=True, text=True)
    assert p.returncode == 0
    # Compute expected using the same escaping logic used by the shim to avoid
    # literal escaping pitfalls in test source.
    expected = raw.replace('\\', '\\\\').replace('"', '\\"')
    assert p.stdout.strip() == expected
