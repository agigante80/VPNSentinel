#!/usr/bin/env bash
# Helper script to update Docker Hub repository description (via Docker Hub API v2)
# Usage:
#   ./scripts/update_dockerhub_description.sh <username> <password_or_token> <namespace/repo> <path_to_markdown>
# Example:
#   ./scripts/update_dockerhub_description.sh myuser mypass agigante80/vpn-sentinel-client dockerhub/client_docker-repository-overview.md
 
# Make this script executable: chmod +x update_dockerhub_description.sh
# Note: This script updates the Docker Hub repository description using the provided markdown file.

set -euo pipefail
if [ "$#" -lt 4 ]; then
  echo "Usage: $0 <username> <password_or_token> <namespace/repo> <path_to_markdown>"
  exit 2
fi
USERNAME=$1
PASSWORD=$2
REPO=$3
MDPATH=$4

if [ ! -f "$MDPATH" ]; then
  echo "Markdown file not found: $MDPATH"
  exit 2
fi

echo "Logging in to Docker Hub..."
# Docker Hub changed auth behavior: prefer Personal Access Tokens (PATs) for repo metadata updates.
# If the provided password/token looks like a PAT, use it directly and skip the /users/login call.
TOKEN=""
USE_BEARER_HEADER=false
if printf '%s' "$PASSWORD" | grep -Eq '^(dhp_|dckr_pat_|[A-Za-z0-9_-]{40,})'; then
  echo "Detected probable Personal Access Token (PAT). Using it directly (no login)."
  # Try exchanging PAT for a usable JWT via the standard login endpoint (username + PAT)
  echo "Exchanging PAT for a Hub JWT via /v2/users/login/ (username + PAT)..."
  LOGIN_JSON=$(mktemp)
  LOGIN_STATUS=$(curl -s -w "%{http_code}" -o "$LOGIN_JSON" -X POST "https://hub.docker.com/v2/users/login/" -H "Content-Type: application/json" -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}")
  if [ "$LOGIN_STATUS" -ge 200 ] && [ "$LOGIN_STATUS" -lt 300 ]; then
    TOKEN=$(cat "$LOGIN_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token',''))")
    echo "Exchanged PAT for JWT via login (HTTP $LOGIN_STATUS)."
  else
    echo "Could not exchange PAT for JWT (HTTP $LOGIN_STATUS). Will try using PAT as a Token header instead."
  fi
  rm -f "$LOGIN_JSON"
  # If exchange failed, we'll fall back to using the raw PAT as a Token-style auth header
  if [ -z "$TOKEN" ]; then
    TOKEN="$PASSWORD"
    USE_BEARER_HEADER=false
    USE_TOKEN_HEADER=true
  else
    USE_TOKEN_HEADER=false
  fi
else
  echo "Logging in to Docker Hub (legacy login to obtain token)..."
  # Login and capture HTTP code and response body
  LOGIN_JSON=$(mktemp)
  LOGIN_STATUS=$(curl -s -w "%{http_code}" -o "$LOGIN_JSON" -X POST "https://hub.docker.com/v2/users/login/" -H "Content-Type: application/json" -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}")
  if [ "$LOGIN_STATUS" -lt 200 ] || [ "$LOGIN_STATUS" -ge 300 ]; then
    echo "ERROR: Docker Hub login failed with HTTP status $LOGIN_STATUS"
    echo "Response body:"
    cat "$LOGIN_JSON" || true
    rm -f "$LOGIN_JSON"
    exit 3
  fi

  TOKEN=$(cat "$LOGIN_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token',''))")
  rm -f "$LOGIN_JSON"

  if [ -z "$TOKEN" ]; then
    echo "ERROR: Failed to obtain token from Docker Hub login response"
    exit 3
  fi
fi

# Build the appropriate Authorization header for subsequent API calls
AUTH_HEADER=""
if [ -n "${TOKEN:-}" ] && [ "${USE_TOKEN_HEADER:-false}" = "true" ]; then
  # Some endpoints accept a 'Token' authorization for raw PATs
  AUTH_HEADER="Authorization: Token ${TOKEN}"
elif [ -n "${TOKEN:-}" ] && [ "${USE_BEARER_HEADER:-false}" = "true" ]; then
  AUTH_HEADER="Authorization: Bearer ${TOKEN}"
else
  # Default to the legacy JWT header which works for tokens obtained via /users/login
  AUTH_HEADER="Authorization: JWT ${TOKEN}"
fi

echo "Preparing payload for $REPO..."
API_URL="https://hub.docker.com/v2/repositories/$REPO/"
PAYLOAD_FILE=$(mktemp)
## Build payload from markdown by reading the file directly to avoid stdin/heredoc timing issues
python3 - <<PY > "$PAYLOAD_FILE"
import json
with open(r"$MDPATH", 'r', encoding='utf-8') as f:
  content = f.read()
print(json.dumps({'full_description': content}))
PY

echo "Checking if repository exists..."
# Check repo existence
REPO_CHECK_RESP_FILE=$(mktemp)
REPO_CHECK_STATUS=$(curl -s -w "%{http_code}" -o "$REPO_CHECK_RESP_FILE" -H "$AUTH_HEADER" "$API_URL")
if [ "$REPO_CHECK_STATUS" -eq 404 ]; then
  echo "Repository not found (404). Attempting to create $REPO..."
  # Extract namespace and repo name
  NAMESPACE=$(echo "$REPO" | cut -d'/' -f1)
  REPO_NAME=$(echo "$REPO" | cut -d'/' -f2)
  CREATE_PAYLOAD=$(mktemp)
  # Use a safe heredoc to avoid argv/indexing issues when constructing JSON
  cat > "$CREATE_PAYLOAD" <<JSON
{
  "name": "${REPO_NAME}",
  "namespace": "${NAMESPACE}",
  "is_private": false,
  "description": ""
}
JSON
  CREATE_RESP_FILE=$(mktemp)
  CREATE_STATUS=$(curl -s -w "%{http_code}" -o "$CREATE_RESP_FILE" -X POST "https://hub.docker.com/v2/repositories/" -H "Content-Type: application/json" -H "$AUTH_HEADER" --data-binary @"$CREATE_PAYLOAD")
  if [ "$CREATE_STATUS" -ge 200 ] && [ "$CREATE_STATUS" -lt 300 ]; then
    echo "Repository created successfully (HTTP $CREATE_STATUS)"
    echo "Create response:" && cat "$CREATE_RESP_FILE" || true
  else
    echo "ERROR: Failed to create repository (HTTP $CREATE_STATUS)"
    echo "Response body:" && cat "$CREATE_RESP_FILE" || true
    rm -f "$REPO_CHECK_RESP_FILE" "$CREATE_PAYLOAD" "$CREATE_RESP_FILE"
    rm -f "$PAYLOAD_FILE"
    exit 5
  fi
  rm -f "$CREATE_PAYLOAD" "$CREATE_RESP_FILE"
elif [ "$REPO_CHECK_STATUS" -ge 200 ] && [ "$REPO_CHECK_STATUS" -lt 300 ]; then
  echo "Repository exists (HTTP $REPO_CHECK_STATUS)"
else
  echo "WARNING: Unexpected response checking repository existence (HTTP $REPO_CHECK_STATUS)"
  echo "Response body:" && cat "$REPO_CHECK_RESP_FILE" || true
fi
rm -f "$REPO_CHECK_RESP_FILE"

echo "Updating repository description for $REPO at $API_URL"

# Retry PATCH a few times in case of transient Docker Hub failures
MAX_RETRIES=3
SLEEP_SECS=2
ATTEMPT=1
while [ $ATTEMPT -le $MAX_RETRIES ]; do
  RESP_FILE=$(mktemp)
  HTTP_STATUS=$(curl -s -w "%{http_code}" -o "$RESP_FILE" -X PATCH "$API_URL" -H "Content-Type: application/json" -H "$AUTH_HEADER" --data-binary @"$PAYLOAD_FILE")

  if [ "$HTTP_STATUS" -ge 200 ] && [ "$HTTP_STATUS" -lt 300 ]; then
    echo "✅ Docker Hub update successful (HTTP $HTTP_STATUS)"
    echo "Response:"
    cat "$RESP_FILE" || true
    rm -f "$RESP_FILE" "$PAYLOAD_FILE"
    echo "Done."
    exit 0
  else
    echo "WARNING: Attempt $ATTEMPT - Docker Hub returned HTTP $HTTP_STATUS"
    echo "Response body:"
    cat "$RESP_FILE" || true
    rm -f "$RESP_FILE"
    ATTEMPT=$((ATTEMPT + 1))
    if [ $ATTEMPT -le $MAX_RETRIES ]; then
      echo "Retrying in $SLEEP_SECS seconds..."
      sleep $SLEEP_SECS
      SLEEP_SECS=$((SLEEP_SECS * 2))
    fi
  fi
done

echo "ERROR: Failed to update Docker Hub repository description after $MAX_RETRIES attempts"
rm -f "$PAYLOAD_FILE"
exit 4
