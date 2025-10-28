#!/usr/bin/env bash
# shellcheck shell=bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOKS_DIR="$ROOT_DIR/.githooks"
GIT_HOOKS_DIR="$ROOT_DIR/.git/hooks"

if [ ! -d "$HOOKS_DIR" ]; then
  echo "No .githooks directory found; nothing to install"
  exit 0
fi

echo "Installing git hooks from $HOOKS_DIR to $GIT_HOOKS_DIR"
mkdir -p "$GIT_HOOKS_DIR"
for hook in "$HOOKS_DIR"/*; do
  name=$(basename "$hook")
  echo " - Installing $name"
  cp "$hook" "$GIT_HOOKS_DIR/$name"
  chmod +x "$GIT_HOOKS_DIR/$name"
done

echo "Git hooks installed."
