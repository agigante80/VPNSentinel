#!/usr/bin/env bash
# lint-shell.sh: run shfmt and ShellCheck over every repo-owned shell script.
#
# Files are selected by behaviour, not by a list: every tracked file shfmt recognises as shell
# (by extension or shebang), minus vendored files. A new script is covered the moment it is
# committed, without anyone remembering to add it here.
#
# Vendored = carries a "# <name>-version: <n>" marker line. That is how forge-kit stamps the
# components it installs and refreshes (the leak-guard scanners today). Reformatting them here
# would turn every refresh into a large conflicting diff, so their style and findings are left
# to upstream (#120, #121).
#
# Usage: scripts/lint-shell.sh            check only, non-zero on any finding
#        scripts/lint-shell.sh --fix      rewrite files with shfmt, then run ShellCheck
#
# Tools come from PATH, or from $SHFMT / $SHELLCHECK. CI pins the versions; a different local
# shfmt can format differently, so use the CI versions when the check disagrees with you.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

SHFMT="${SHFMT:-shfmt}"
SHELLCHECK="${SHELLCHECK:-shellcheck}"
FIX=0
case "${1:-}" in
  --fix) FIX=1 ;;
  "") ;;
  *)
    echo "usage: $0 [--fix]" >&2
    exit 2
    ;;
esac

files=()
vendored=()
while IFS= read -r f; do
  if grep -qE '^# *[a-z0-9-]+-version: [0-9]+$' "$f"; then
    vendored+=("$f")
  else
    files+=("$f")
  fi
done < <(git ls-files -z | xargs -0 "$SHFMT" -f | LC_ALL=C sort)

# A selector that matches nothing passes vacuously, so an empty selection is a failure.
if [ "${#files[@]}" -eq 0 ]; then
  echo "lint-shell: selected no shell scripts; the selector is broken" >&2
  exit 1
fi

echo "lint-shell: ${#files[@]} scripts, ${#vendored[@]} vendored skipped (${vendored[*]:-none})"

if [ "$FIX" = 1 ]; then
  "$SHFMT" -i 2 -ci -w "${files[@]}"
fi

status=0
"$SHFMT" -i 2 -ci -d "${files[@]}" || status=1
"$SHELLCHECK" -x "${files[@]}" || status=1

if [ "$status" = 0 ]; then
  echo "lint-shell: clean"
fi
exit "$status"
