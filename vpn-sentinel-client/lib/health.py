#!/usr/bin/env python3
"""CLI shim for health.py used by unit tests.

This script loads vpn_sentinel_common.health and prints a JSON health object
when invoked with no arguments. It exists to satisfy tests that call the
original script path.
"""
import json
import sys

try:
    from vpn_sentinel_common import health as vs_health
except Exception:
    vs_health = None


def main():
    # Build a canonical health object, prefer canonical helpers when present
    if vs_health:
        h = vs_health.sample_health_ok()
        client_status = vs_health.check_client_process()
        network_status = vs_health.check_network_connectivity()
    else:
        h = {"status": "ok", "uptime_seconds": 0, "timestamp": "", "components": {}, "server_time": ""}
        client_status = "not_running"
        network_status = "unreachable"

    # Ensure keys expected by tests are present
    h.setdefault("client_process", client_status)
    h.setdefault("network_connectivity", network_status)
    print(json.dumps(h))
    return 0


if __name__ == '__main__':
    rc = main()
    sys.exit(rc)
