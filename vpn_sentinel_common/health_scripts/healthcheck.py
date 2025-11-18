#!/usr/bin/env python3
"""VPN Sentinel Health Check Script (Python version).

Replaces the shell-based healthcheck.sh with a pure Python implementation.
Performs comprehensive health checks for VPN Sentinel client components.
"""
import os
import sys
import json
import subprocess
import time
from pathlib import Path

# Add the parent directory to sys.path so we can import vpn_sentinel_common
sys.path.insert(0, str(Path(__file__).parent.parent))

from vpn_sentinel_common import health
from vpn_sentinel_common.log_utils import log_info, log_warn, log_error


def check_client_process():
    """Check if VPN Sentinel client process is running."""
    return health.check_client_process()


def check_network_connectivity():
    """Check network connectivity."""
    return health.check_network_connectivity()


def check_server_connectivity():
    """Check VPN Sentinel server connectivity."""
    return health.check_server_connectivity()


def check_dns_leak_detection():
    """Check DNS leak detection."""
    return health.check_dns_leak_detection()


def get_system_info():
    """Get system information."""
    return health.get_system_info()


def check_health_monitor_running():
    """Check if health monitor is running."""
    try:
        # Check for health monitor process
        result = subprocess.run(
            ['pgrep', '-f', 'health-monitor'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False


def check_health_monitor_endpoint():
    """Check if health monitor endpoint is responding."""
    try:
        import requests
        health_port = os.getenv('VPN_SENTINEL_HEALTH_PORT', '8082')
        response = requests.get(f'http://localhost:{health_port}/health', timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def check_system_resources():
    """Check system resources (memory and disk usage)."""
    warnings = []

    try:
        # Check memory usage
        with open('/proc/meminfo', 'r') as f:
            mem_info = {}
            for line in f:
                if ':' in line:
                    key, value = line.split(':', 1)
                    mem_info[key.strip()] = value.strip()

        if 'MemTotal' in mem_info and 'MemAvailable' in mem_info:
            total_kb = int(mem_info['MemTotal'].split()[0])
            available_kb = int(mem_info['MemAvailable'].split()[0])
            used_percent = ((total_kb - available_kb) / total_kb) * 100

            if used_percent > 90:
                warnings.append('high_memory_usage')
                log_warn('health', f'High memory usage: {used_percent:.1f}%')
    except Exception:
        pass

    try:
        # Check disk usage
        result = subprocess.run(
            ['df', '/', '--output=pcent'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                percent_str = lines[1].strip().rstrip('%')
                try:
                    disk_percent = int(percent_str)
                    if disk_percent > 90:
                        warnings.append('high_disk_usage')
                        log_warn('health', f'High disk usage: {disk_percent}%')
                except ValueError:
                    pass
    except Exception:
        pass

    return warnings


def perform_health_checks():
    """Perform all health checks and return results."""
    results = {}

    # Client process check
    results['client_process'] = check_client_process()

    # Health monitor checks
    monitor_running = check_health_monitor_running()
    results['health_monitor_running'] = monitor_running

    if monitor_running:
        results['health_monitor_responding'] = check_health_monitor_endpoint()
    else:
        results['health_monitor_responding'] = False

    # Network connectivity
    results['network_connectivity'] = check_network_connectivity()

    # Server connectivity - Set to 'not_checked' instead of checking
    # RATIONALE: Client already proves server connectivity by successfully POSTing keepalives.
    # The old check made unauthenticated HEAD/GET requests to server root causing 401 errors in logs.
    # If keepalive succeeds, server is reachable. This check is redundant and noisy.
    results['server_connectivity'] = 'not_checked'

    # DNS leak detection
    results['dns_leak_detection'] = check_dns_leak_detection()

    # System resources
    results['system_warnings'] = check_system_resources()

    return results


def determine_overall_health(results):
    """Determine overall health status."""
    # Network failure is considered unhealthy
    if results['network_connectivity'] != 'healthy':
        return False

    # Client process should be healthy
    if results['client_process'] != 'healthy':
        return False

    return True


def print_human_readable(results, overall_healthy):
    """Print human-readable health summary."""
    if overall_healthy:
        log_info('health', '✅ VPN Sentinel client is healthy')
    else:
        log_error('health', '❌ VPN Sentinel client has health issues')

    # Client status
    if results['client_process'] == 'healthy':
        log_info('health', 'Client process: healthy')
    else:
        log_error('health', f'Client process: {results["client_process"]}')

    # Health monitor status
    if results['health_monitor_running']:
        log_info('health', 'Health monitor: running')
        if results['health_monitor_responding']:
            log_info('health', 'Health monitor endpoint: responding')
        else:
            log_warn('health', 'Health monitor endpoint: not responding')
    else:
        log_info('health', 'Health monitor: not running (optional)')

    # Network status
    if results['network_connectivity'] == 'healthy':
        log_info('health', 'Network connectivity: healthy')
    else:
        log_error('health', f'Network connectivity: {results["network_connectivity"]}')

    # Server status
    if results['server_connectivity'] == 'healthy':
        log_info('health', 'Server connectivity: healthy')
    elif results['server_connectivity'] == 'unreachable':
        log_warn('health', f'Server connectivity: unreachable')
    else:
        log_info('health', f'Server connectivity: {results["server_connectivity"]}')

    # DNS leak detection
    if results['dns_leak_detection'] == 'healthy':
        log_info('health', 'DNS leak detection: healthy')
    else:
        log_warn('health', f'DNS leak detection: {results["dns_leak_detection"]}')

    # System warnings
    if results['system_warnings']:
        log_warn('health', f'System warnings: {", ".join(results["system_warnings"])}')


def print_json(results, overall_healthy):
    """Print JSON health report."""
    status = 'healthy' if overall_healthy else 'unhealthy'
    timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    # Map results to expected JSON structure
    checks = {
        'client_process': results['client_process'],
        'network_connectivity': results['network_connectivity'],
        'server_connectivity': results['server_connectivity'],
        'health_monitor': 'running' if results['health_monitor_running'] else 'not_running'
    }

    # Convert warnings to the expected format
    warnings = []
    if results['server_connectivity'] == 'unreachable':
        warnings.append('server_unreachable')
    if not results['health_monitor_responding'] and results['health_monitor_running']:
        warnings.append('monitor_not_responding')
    warnings.extend(results['system_warnings'])

    output = {
        'status': status,
        'timestamp': timestamp,
        'checks': checks,
        'warnings': warnings
    }

    print(json.dumps(output, indent=2))


def main():
    """Main entry point."""
    results = perform_health_checks()
    overall_healthy = determine_overall_health(results)

    # Print human-readable output
    print_human_readable(results, overall_healthy)

    # Print JSON if requested
    if len(sys.argv) > 1 and sys.argv[1] == '--json':
        print()  # Add newline before JSON
        print_json(results, overall_healthy)

    # Exit with appropriate code
    sys.exit(0 if overall_healthy else 1)


if __name__ == '__main__':
    main()