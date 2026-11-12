#!/usr/bin/env bash
# shellcheck shell=bash
# Generate the README dashboard screenshot from fixed demo data (issue #147).
#
# Runs scripts/dashboard_demo.py, which serves the dashboard with four demo clients
# (2 green, 1 yellow DNS leak, 1 red VPN bypass) and a demo server identity. Every IP is
# from the documentation ranges, and no geolocation lookup happens, so the screenshot can
# never contain the real public IP of the machine that takes it.
#
# Usage: scripts/generate_dashboard_screenshot.sh [output.png]
# Env:   DEMO_PORT (default 18090), VERSION (shown in the footer, default: derived)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT="${1:-${ROOT_DIR}/docs/images/dashboard-screenshot.png}"
PORT="${DEMO_PORT:-18090}"
URL="http://127.0.0.1:${PORT}/dashboard"

if [ -z "${VERSION:-}" ]; then
  VERSION="$("${SCRIPT_DIR}/get_version.sh" 2>/dev/null | sed 's/-.*//' || true)"
fi
export VERSION

BROWSER=""
for candidate in chromium-browser chromium google-chrome; do
  if command -v "$candidate" >/dev/null 2>&1; then
    BROWSER="$candidate"
    break
  fi
done
if [ -z "$BROWSER" ]; then
  echo "No headless Chromium or Chrome found (tried chromium-browser, chromium, google-chrome)" >&2
  exit 1
fi

PYTHONPATH="${ROOT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}" python3 "${SCRIPT_DIR}/dashboard_demo.py" "$PORT" &
DEMO_PID=$!
trap 'kill "$DEMO_PID" 2>/dev/null || true' EXIT

for _ in $(seq 1 50); do
  if curl -sf "$URL" >/dev/null 2>&1; then
    break
  fi
  if ! kill -0 "$DEMO_PID" 2>/dev/null; then
    echo "Demo dashboard exited before serving" >&2
    exit 1
  fi
  sleep 0.2
done
curl -sf "$URL" >/dev/null

PROFILE_DIR="$(mktemp -d)"
trap 'kill "$DEMO_PID" 2>/dev/null || true; rm -rf "$PROFILE_DIR"' EXIT

"$BROWSER" --headless=new --disable-gpu --hide-scrollbars --user-data-dir="$PROFILE_DIR" \
  --run-all-compositor-stages-before-draw --virtual-time-budget=3000 \
  --window-size=1400,1000 --screenshot="$OUT" "$URL" >/dev/null 2>&1

if [ ! -s "$OUT" ]; then
  echo "Screenshot was not written: $OUT" >&2
  exit 1
fi
echo "Saved $OUT (browser: $BROWSER, version shown: ${VERSION:-unknown})"
