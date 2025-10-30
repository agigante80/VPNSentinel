#!/usr/bin/env python3
"""
Test compatibility wrapper for the health shim.

Some unit tests look for `tests/vpn-sentinel-client/lib/health.py` and execute
it as a script. To avoid duplicating logic, this wrapper executes the real
shim located at the repository top-level `vpn-sentinel-client/lib/health.py`.
"""
from pathlib import Path
import runpy


def main() -> None:
    # Path structure: tests/vpn-sentinel-client/lib/health.py
    # parents[0] -> lib, parents[1] -> vpn-sentinel-client, parents[2] -> tests, parents[3] -> repo root
    root_shim = Path(__file__).resolve().parents[3] / "vpn-sentinel-client" / "lib" / "health.py"
    runpy.run_path(str(root_shim), run_name="__main__")


if __name__ == "__main__":
    main()
