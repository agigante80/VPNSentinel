#!/usr/bin/env bash
set -euo pipefail
# Simple wrapper to manage a server-side health monitor process (start/stop)
# For tests, set VPN_SENTINEL_SERVER_DUMMY_CMD to point to a command to run.

PIDFILE=${VPN_SENTINEL_SERVER_HEALTH_PIDFILE:-/tmp/vpn-sentinel-server-health.pid}
CMD=${VPN_SENTINEL_SERVER_DUMMY_CMD:-}

usage() {
  echo "Usage: $0 [--stop]"
  exit 2
}

if [ "${1:-}" = "--stop" ]; then
  if [ ! -f "$PIDFILE" ]; then
    echo "No pidfile at $PIDFILE; nothing to stop"
    exit 0
  fi
  PID=$(cat "$PIDFILE" 2>/dev/null || true)
  if [ -z "$PID" ]; then
    echo "Empty pidfile; removing"
    rm -f "$PIDFILE"
    exit 0
  fi
  echo "Stopping process $PID from pidfile $PIDFILE"
  kill "$PID" 2>/dev/null || true
  # give it a moment to exit
  sleep 1
  if kill -0 "$PID" 2>/dev/null; then
    echo "Process $PID did not exit; force killing"
    kill -9 "$PID" 2>/dev/null || true
  fi
  rm -f "$PIDFILE"
  echo "Stopped"
  exit 0
fi

if [ -z "$CMD" ]; then
  # Default to running the Python health monitor in this repo
  PY_MONITOR="$(dirname "$0")/health-monitor.py"
  if [ -f "$PY_MONITOR" ]; then
    CMD="python3 ${PY_MONITOR}"
  else
    echo "ERROR: no command to start. Set VPN_SENTINEL_SERVER_DUMMY_CMD for tests or ensure vpn-sentinel-server/health-monitor.py exists."
    exit 2
  fi
fi

if [ -f "$PIDFILE" ]; then
  OLD_PID=$(cat "$PIDFILE" 2>/dev/null || true)
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Process already running with pid $OLD_PID"
    exit 0
  else
    echo "Stale pidfile found; removing"
    rm -f "$PIDFILE"
  fi
fi

echo "Starting command: $CMD"
# Start the monitor in the background but keep its stdout/stderr attached so
# Docker container logs will include the monitor output (useful for tests).
# shellcheck disable=SC2086
sh -c "$CMD" &
PID=$!
echo "$PID" > "$PIDFILE"
echo "Started pid $PID (pidfile: $PIDFILE)"
exit 0
