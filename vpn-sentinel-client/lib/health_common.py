#!/usr/bin/env python3
"""Small CLI shim for health_common helpers used by the unit tests.

This script exposes a tiny command-line interface mirroring the original
shell shim so tests can invoke it directly. It imports the canonical
implementation from vpn_sentinel_common.health when available and falls
back to embedded helpers when necessary.
"""
import sys
import json

try:
    from vpn_sentinel_common import health as vs_health
except Exception:
    vs_health = None


def get_system_info_json():
    if vs_health:
        data = vs_health.get_system_info()
    else:
        data = {"memory_percent": "unknown", "disk_percent": "unknown"}
    print(json.dumps(data))
    return 0


def check_client_process():
    if vs_health:
        print(vs_health.check_client_process())
        return 0
    print("not_running")
    return 1


def check_network_connectivity():
    if vs_health:
        print(vs_health.check_network_connectivity())
        return 0
    print("unreachable")
    return 1


def generate_health_status():
    if vs_health:
        print(json.dumps(vs_health.sample_health_ok()))
        return 0
    print(json.dumps({"status": "ok", "checks": {}}))
    return 0


def main(argv):
    if len(argv) < 2:
        print("usage: health_common.py <command>")
        return 2
    cmd = argv[1]
    if cmd == "get_system_info":
        return get_system_info_json()
    if cmd == "check_client_process":
        return check_client_process()
    if cmd == "check_network_connectivity":
        return check_network_connectivity()
    if cmd == "generate_health_status":
        return generate_health_status()
    print("unknown command")
    return 2


if __name__ == '__main__':
    rc = main(sys.argv)
    sys.exit(rc)
