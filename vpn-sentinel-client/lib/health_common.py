#!/usr/bin/env python3
"""VPN Sentinel health common CLI shim

Provides small command-line interface compatible with existing shell
lib/health-common.sh functions:
- check_client_process
- check_network_connectivity
- check_server_connectivity
- check_dns_leak_detection
- get_system_info

Intended to be used by shell wrappers (health-monitor.sh) as a replacement.
"""
import argparse
import json
import os
import subprocess
import time
#!/usr/bin/env python3
"""VPN Sentinel health common CLI shim

This file is a thin shim used during an incremental migration. It prefers
the canonical implementation in `vpn_sentinel_common.health_common`. If the
package is not available (for example in older Docker or test contexts),
the local fallback implementation below is used so existing shell wrappers
and tests continue to work.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from typing import Dict

_USING_CANONICAL = False
try:
    # Prefer the canonical implementation when available
    from vpn_sentinel_common.health_common import (
        check_client_process as _check_client_process,
        check_network_connectivity as _check_network_connectivity,
        check_server_connectivity as _check_server_connectivity,
        check_dns_leak_detection as _check_dns_leak_detection,
        get_system_info as _get_system_info,
        generate_health_status as _generate_health_status,
    )

    _USING_CANONICAL = True
except Exception:
    # Fall back to the local implementations below
    _USING_CANONICAL = False


def _run(cmd):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, shell=False)
        return p.stdout.strip(), p.returncode
    except Exception:
        return "", 1


def check_client_process() -> str:
    if _USING_CANONICAL:
        return _check_client_process()
    out, rc = _run(["sh", "-c", "pgrep -f 'vpn-sentinel-client.sh' >/dev/null 2>&1 && echo healthy || echo not_running"]) 
    return out or "not_running"


def check_network_connectivity() -> str:
    if _USING_CANONICAL:
        return _check_network_connectivity()
    out, rc = _run(["sh", "-c", "curl -f -s --max-time 5 \"https://1.1.1.1/cdn-cgi/trace\" >/dev/null 2>&1 && echo healthy || echo unreachable"]) 
    return out or "unreachable"


def check_server_connectivity() -> str:
    if _USING_CANONICAL:
        return _check_server_connectivity()
    server_url = os.environ.get("VPN_SENTINEL_URL", "")
    if not server_url:
        return "not_configured"
    out, rc = _run(["sh", "-c", f"curl -s --max-time 10 -I '{server_url}' >/dev/null 2>&1 && echo healthy || echo unreachable"]) 
    return out or "unreachable"


def check_dns_leak_detection() -> str:
    if _USING_CANONICAL:
        return _check_dns_leak_detection()
    out, rc = _run(["sh", "-c", "curl -f -s --max-time 5 \"https://ipinfo.io/json\" >/dev/null 2>&1 && echo healthy || echo unavailable"]) 
    return out or "unavailable"


def get_system_info() -> Dict[str, str]:
    if _USING_CANONICAL:
        return _get_system_info()

    memory_percent = "unknown"
    disk_percent = "unknown"

    try:
        # try /proc/meminfo first
        with open('/proc/meminfo', 'r') as f:
            mem_total = None
            mem_avail = None
            for line in f:
                if line.startswith('MemTotal:'):
                    mem_total = int(line.split()[1])
                elif line.startswith('MemAvailable:'):
                    mem_avail = int(line.split()[1])
            if mem_total and mem_avail:
                memory_percent = "{:.1f}".format((1 - mem_avail / mem_total) * 100)
    except Exception:
        pass

    try:
        p = subprocess.run(["df", "/"], capture_output=True, text=True)
        if p.returncode == 0:
            lines = p.stdout.strip().split('\n')
            if len(lines) > 1:
                disk_percent = lines[1].split()[4].rstrip('%')
    except Exception:
        pass

    return {"memory_percent": memory_percent, "disk_percent": disk_percent}


def generate_health_status() -> Dict:
    if _USING_CANONICAL:
        return _generate_health_status()
    client_status = check_client_process()
    net_status = check_network_connectivity()
    dns_status = check_dns_leak_detection()
    system_info = get_system_info()
    overall = 'healthy'
    issues = []
    if client_status != 'healthy':
        overall = 'unhealthy'
        issues.append('client_process_not_running')
    if net_status != 'healthy':
        overall = 'unhealthy'
        issues.append('network_unreachable')
    if dns_status != 'healthy':
        if overall != 'unhealthy':
            overall = 'degraded'
        issues.append('dns_detection_unavailable')
    out = {
        'status': overall,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'checks': {
            'client_process': client_status,
            'network_connectivity': net_status,
            'dns_leak_detection': dns_status
        },
        'system': system_info,
        'issues': issues
    }
    return out


def cli() -> None:
    p = argparse.ArgumentParser(prog='health_common')
    p.add_argument('command', choices=[
        'check_client_process',
        'check_network_connectivity',
        'check_server_connectivity',
        'check_dns_leak_detection',
        'get_system_info',
        'generate_health_status'
    ])
    p.add_argument('--json', action='store_true', help='Output JSON for some commands')
    args = p.parse_args()

    if args.command == 'check_client_process':
        print(check_client_process())
    elif args.command == 'check_network_connectivity':
        print(check_network_connectivity())
    elif args.command == 'check_server_connectivity':
        print(check_server_connectivity())
    elif args.command == 'check_dns_leak_detection':
        print(check_dns_leak_detection())
    elif args.command == 'get_system_info':
        info = get_system_info()
        if args.json:
            print(json.dumps(info))
        else:
            print(json.dumps(info))
    elif args.command == 'generate_health_status':
        out = generate_health_status()
        print(json.dumps(out))


if __name__ == '__main__':
    cli()
