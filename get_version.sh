#!/bin/bash
# VPN Sentinel Version Determination Script
# This script determines the version based on Git context

set -e

# Get the current branch
BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Get git describe output
GIT_DESCRIBE=$(git describe --tags --always --dirty=-dirty 2>/dev/null || echo "v0.0.0-0-g$(git rev-parse --short HEAD)")

# Parse git describe output
# Format: v{major}.{minor}.{patch}[-{commits}-g{hash}][-dirty]
if [[ $GIT_DESCRIBE =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)(.*)$ ]]; then
  MAJOR="${BASH_REMATCH[1]}"
  MINOR="${BASH_REMATCH[2]}"
  PATCH="${BASH_REMATCH[3]}"
  SUFFIX="${BASH_REMATCH[4]}"

  BASE_VERSION="${MAJOR}.${MINOR}.${PATCH}"

  # Determine version based on branch and git status
  if [ "$BRANCH" = "main" ]; then
    if [[ $SUFFIX =~ ^$ ]]; then
      # Clean tag on main branch - use base version
      VERSION="$BASE_VERSION"
    else
      # Commits ahead on main - use base version with build info
      COMMITS_AHEAD=$(echo "$SUFFIX" | sed -n 's/-\([0-9]\+\)-.*/\1/p')
      if [ -n "$COMMITS_AHEAD" ] && [ "$COMMITS_AHEAD" != "0" ]; then
        VERSION="${BASE_VERSION}+${COMMITS_AHEAD}"
      else
        VERSION="$BASE_VERSION"
      fi
    fi
  elif [ "$BRANCH" = "develop" ]; then
    # Develop branch - always use dev suffix with commit hash
    COMMIT_HASH=$(git rev-parse --short HEAD)
    VERSION="${BASE_VERSION}-dev-${COMMIT_HASH}"
  else
    # Other branches - use branch name with commit hash
    COMMIT_HASH=$(git rev-parse --short HEAD)
    VERSION="${BASE_VERSION}-${BRANCH}-${COMMIT_HASH}"
  fi
else
  # Fallback if git describe fails
  COMMIT_HASH=$(git rev-parse --short HEAD)
  VERSION="0.0.0-dev-${COMMIT_HASH}"
fi

echo "$VERSION"
