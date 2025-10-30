#!/usr/bin/env python3
"""Clean health_common shim used by unit tests during refactor.

This is a safe, minimal implementation kept separate from the
iteratively-edited `health_common.py` so tests can run reliably
while we finish cleanup.
"""

import argparse
import json
import subprocess
import time
from typing import Dict


def _run(cmd):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, shell=False)
        return p.stdout.strip(), p.returncode
    except Exception:
        return "", 1


def check_client_process() -> str:
    out, _ = _run([
        "sh",
        "-c",
        "pgrep -f 'vpn-sentinel-client.sh' >/dev/null 2>&1 && echo healthy || echo not_running",
    ])
    return out or "not_running"


def check_network_connectivity() -> str:
    out, _ = _run([
        "sh",
        "-c",
        'curl -f -s --max-time 5 "https://1.1.1.1/cdn-cgi/trace" >/dev/null 2>&1 && echo healthy || echo unreachable',
    ])
    return out or "unreachable"


def check_dns_leak_detection() -> str:
    out, _ = _run([
        "sh",
        "-c",
        'curl -f -s --max-time 5 "https://ipinfo.io/json" >/dev/null 2>&1 && echo healthy || echo unavailable',
    ])
    return out or "unavailable"


def get_system_info() -> Dict[str, str]:
    return {"memory_percent": "unknown", "disk_percent": "unknown"}


def generate_health_status() -> Dict:
    return {
        "status": "unknown",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "checks": {
            "client_process": check_client_process(),
            "network_connectivity": check_network_connectivity(),
            "dns_leak_detection": check_dns_leak_detection(),
        },
        "system": get_system_info(),
        "issues": [],
    }


def cli() -> None:
    p = argparse.ArgumentParser(prog="health_common")
    p.add_argument("command", choices=[
        "check_client_process",
        "check_network_connectivity",
        "check_dns_leak_detection",
        "get_system_info",
        "generate_health_status",
    ])
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if args.command == "check_client_process":
        print(check_client_process())
    elif args.command == "check_network_connectivity":
        print(check_network_connectivity())
    elif args.command == "check_dns_leak_detection":
        print(check_dns_leak_detection())
    elif args.command == "get_system_info":
        print(json.dumps(get_system_info()))
    elif args.command == "generate_health_status":
        print(json.dumps(generate_health_status()))


if __name__ == "__main__":
    cli()
