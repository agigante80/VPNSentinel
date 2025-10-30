#!/usr/bin/env bash
# shellcheck shell=bash
set -eu

# Resolve script directory; fall back to $0 when BASH_SOURCE is not available
_src=${BASH_SOURCE[0]:-${0}}
SCRIPT_DIR="$(cd "$(dirname "${_src}")" && pwd -P)"
PY="${SCRIPT_DIR}/health-monitor.py"
PIDFILE="${VPN_SENTINEL_HEALTH_PIDFILE:-/tmp/vpn-sentinel-health-monitor.pid}"

if command -v python3 >/dev/null 2>&1 && [ -f "${PY}" ]; then
  exec python3 "${PY}" "$@"
fi

case "${1:-}" in
  --stop)
    if [ -f "${PIDFILE}" ]; then
      pid="$(cat "${PIDFILE}" 2>/dev/null || true)"
      if [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null; then
        if [ "$(ps -o uid= -p "${pid}" 2>/dev/null | tr -d ' \t\n' || true)" = "$(id -u)" ]; then
          kill -TERM "${pid}" 2>/dev/null || true
          sleep 1
          kill -KILL "${pid}" 2>/dev/null || true
          rm -f "${PIDFILE}" 2>/dev/null || true
          exit 0
        else
          printf '%s\n' "Refusing to stop pid ${pid}: not owned" >&2
          exit 3
        fi
      else
        rm -f "${PIDFILE}" 2>/dev/null || true
      fi
    fi
    exit 0
    ;;
  --help|-h|"")
    printf '%s\n' "--stop, --help"
    exit 0
    ;;
  *)
    printf '%s\n' "Unknown option: %s" "${1:-}" >&2
    exit 2
    ;;
esac
