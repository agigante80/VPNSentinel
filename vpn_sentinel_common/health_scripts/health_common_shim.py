#!/usr/bin/env python3
"""
Health CLI shim for backward compatibility with tests.
Provides the same CLI interface as the old health_common.py script.
"""

import json
import sys
from vpn_sentinel_common.health_scripts.healthcheck import (
    check_client_process,
    check_network_connectivity,
    get_system_info,
    perform_health_checks,
    determine_overall_health,
    print_json
)


def main():
    if len(sys.argv) < 2:
        print("Usage: health_common.py <command> [options]", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "get_system_info":
            info = get_system_info()
            if "--json" in sys.argv:
                print(json.dumps(info))
            else:
                for key, value in info.items():
                    print(f"{key}: {value}")

        elif command == "check_client_process":
            result = check_client_process()
            print(result)

        elif command == "check_network_connectivity":
            result = check_network_connectivity()
            print(result)

        elif command == "generate_health_status":
            results = perform_health_checks()
            overall_healthy = determine_overall_health(results)
            output = {
                "status": "healthy" if overall_healthy else "unhealthy",
                "checks": results
            }
            print(json.dumps(output))

        else:
            print(f"Unknown command: {command}", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()