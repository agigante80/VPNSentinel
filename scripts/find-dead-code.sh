#!/usr/bin/env bash
# shellcheck shell=bash
# Whole-program dead-code scan for VPNSentinel (vulture).
# Finds unused functions/classes/methods/branches that flake8's local rules miss.
# Companion to the .claude/skills/find-dead-code skill: candidates, NOT verdicts —
# verify each against dynamic refs, then confirm with `pytest tests/unit/` + `bin/local-env verify`.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

TARGET="src/vpn_sentinel"
ALLOWLIST="$REPO_ROOT/.vulture_allowlist.py"
CONF=60

usage() {
  cat <<'EOF'
Usage: scripts/find-dead-code.sh [confidence|--baseline]

  (no args)     scan src/vpn_sentinel/ at min-confidence 60, applying .vulture_allowlist.py
  <number>      scan at the given min-confidence (e.g. 80 = higher signal, fewer hits)
  --baseline    regenerate .vulture_allowlist.py from current findings (REVIEW before committing —
                this whitelists everything currently flagged, including any genuine dead code)
  -h|--help     this help
EOF
}

if ! python3 -c "import vulture" >/dev/null 2>&1; then
  echo "vulture is not installed (it is a dev-only dep in tests/requirements.txt)." >&2
  echo "Install it, e.g.:  python3 -m pip install vulture   (use a venv if PEP 668 blocks it)" >&2
  exit 2
fi

case "${1:-}" in
  -h | --help)
    usage
    exit 0
    ;;
  --baseline)
    echo "Regenerating $ALLOWLIST from current findings (review before committing)..."
    python3 -m vulture "$TARGET" --make-whitelist >"$ALLOWLIST" || true
    echo "Wrote $ALLOWLIST ($(grep -c . "$ALLOWLIST" 2>/dev/null || echo 0) lines). Prune real dead code out of it before committing."
    exit 0
    ;;
  '') ;;
  *)
    if [[ "$1" =~ ^[0-9]+$ ]]; then
      CONF="$1"
    else
      echo "Unknown argument: $1" >&2
      usage
      exit 2
    fi
    ;;
esac

ARGS=("$TARGET")
[ -f "$ALLOWLIST" ] && ARGS+=("$ALLOWLIST")

echo "vulture scan: $TARGET (min-confidence $CONF, allowlist: $([ -f "$ALLOWLIST" ] && echo applied || echo none))"
echo "--- candidates (verify dynamic refs before deleting; see .claude/skills/find-dead-code) ---"
python3 -m vulture "${ARGS[@]}" --min-confidence "$CONF"
