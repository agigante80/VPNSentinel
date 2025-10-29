"""Small client-side shim to call vpn_sentinel_common.geolocation from shell.

This script is intended to be invoked as:
  python3 -m vpn-sentinel-client.lib.geo_client --service auto --timeout 5
and will print a JSON object to stdout with the same keys as
`vpn_sentinel_common.geolocation.get_geolocation`.
"""
from __future__ import annotations

import argparse
import json
import sys


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", default="auto")
    parser.add_argument("--timeout", type=int, default=5)
    args = parser.parse_args(argv)

    try:
        # Import from local package path if available
        from vpn_sentinel_common.geolocation import get_geolocation
    except Exception:
        # try relative import for older layouts
        try:
            from vpn_sentinel_common.geolocation import get_geolocation
        except Exception as exc:
            print(json.dumps({}), end="")
            return 2

    result = get_geolocation(service=args.service, timeout=args.timeout)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
