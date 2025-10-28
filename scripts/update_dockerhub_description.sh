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
TOKEN_RESP=$(curl -s -X POST "https://hub.docker.com/v2/users/login/" -H "Content-Type: application/json" -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}")
TOKEN=$(echo "$TOKEN_RESP" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token',''))")
if [ -z "$TOKEN" ]; then
  echo "Failed to obtain token from Docker Hub. Response: $TOKEN_RESP"
  exit 3
fi

echo "Updating repository description for $REPO..."
# Docker Hub API endpoint for repository details
API_URL="https://hub.docker.com/v2/repositories/$REPO/"

# Payload: update full_description field
PAYLOAD=$(python3 - <<PY
import json,sys
print(json.dumps({
  'full_description': open(sys.argv[1],'r',encoding='utf-8').read()
}))
PY
"$MDPATH")

HTTP_RESP=$(curl -s -X PATCH "$API_URL" -H "Content-Type: application/json" -H "Authorization: JWT $TOKEN" -d "$PAYLOAD")

echo "Response: $HTTP_RESP"

echo "Done."
