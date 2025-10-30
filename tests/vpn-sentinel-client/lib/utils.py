#!/usr/bin/env python3
"""
Test compatibility wrapper for the utils shim.

Some unit tests execute `tests/vpn-sentinel-client/lib/utils.py`. To avoid
duplicating logic, this wrapper executes the real shim at
`vpn-sentinel-client/lib/utils.py`.
"""
from pathlib import Path
import runpy


def main() -> None:
    root_shim = Path(__file__).resolve().parents[3] / "vpn-sentinel-client" / "lib" / "utils.py"
    runpy.run_path(str(root_shim), run_name="__main__")


if __name__ == "__main__":
    main()
