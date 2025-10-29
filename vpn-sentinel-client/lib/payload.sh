#!/usr/bin/env bash
# shellcheck shell=bash
# Payload helpers for vpn-sentinel-client
# Sourced by vpn-sentinel-client.sh

build_payload() {
	# Args: none, uses global variables populated by get_vpn_info/get_dns_info
	TIMESTAMP=$(date +"%Y-%m-%dT%H:%M:%S%z")
	if command -v jq >/dev/null 2>&1; then
		# Use jq to build JSON safely (avoids quoting issues)
		printf '%s' '{}' | jq --arg client_id "$CLIENT_ID" \
			--arg timestamp "$TIMESTAMP" \
			--arg public_ip "${PUBLIC_IP:-unknown}" \
			--arg country "${COUNTRY:-Unknown}" \
			--arg city "${CITY:-Unknown}" \
			--arg region "${REGION:-Unknown}" \
			--arg org "${ORG:-Unknown}" \
			--arg timezone "${VPN_TIMEZONE:-Unknown}" \
			--arg dns_loc "${DNS_LOC:-Unknown}" \
			--arg dns_colo "${DNS_COLO:-Unknown}" \
			'.client_id=$client_id | .timestamp=$timestamp | .public_ip=$public_ip | .status="alive" | .location={country:$country,city:$city,region:$region,org:$org,timezone:$timezone} | .dns_test={location:$dns_loc,colo:$dns_colo}'
	else
		# Fallback to shell-built JSON (less safe)
		JSON_DATA="{\n"
		JSON_DATA="$JSON_DATA  \"client_id\": \"$(json_escape "$CLIENT_ID")\",\n"
		JSON_DATA="$JSON_DATA  \"timestamp\": \"$(json_escape "$TIMESTAMP")\",\n"
		JSON_DATA="$JSON_DATA  \"public_ip\": \"$(json_escape "${PUBLIC_IP:-unknown}")\",\n"
		JSON_DATA="$JSON_DATA  \"status\": \"alive\",\n"
		JSON_DATA="$JSON_DATA  \"location\": {\n"
		JSON_DATA="$JSON_DATA    \"country\": \"$(json_escape "${COUNTRY:-Unknown}")\",\n"
		JSON_DATA="$JSON_DATA    \"city\": \"$(json_escape "${CITY:-Unknown}")\",\n"
		JSON_DATA="$JSON_DATA    \"region\": \"$(json_escape "${REGION:-Unknown}")\",\n"
		JSON_DATA="$JSON_DATA    \"org\": \"$(json_escape "${ORG:-Unknown}")\",\n"
		JSON_DATA="$JSON_DATA    \"timezone\": \"$(json_escape "${VPN_TIMEZONE:-Unknown}")\"\n"
		JSON_DATA="$JSON_DATA  },\n"
		JSON_DATA="$JSON_DATA  \"dns_test\": {\n"
		JSON_DATA="$JSON_DATA    \"location\": \"$(json_escape "${DNS_LOC:-Unknown}")\",\n"
		JSON_DATA="$JSON_DATA    \"colo\": \"$(json_escape "${DNS_COLO:-Unknown}")\"\n"
		JSON_DATA="$JSON_DATA  }\n"
		JSON_DATA="$JSON_DATA}"

		printf '%s' "$JSON_DATA"
	fi
}

post_payload() {
	PAYLOAD="$1"
	# Test hook: when VPN_SENTINEL_TEST_CAPTURE_PATH is set, append payload to that file
	if [ -n "${VPN_SENTINEL_TEST_CAPTURE_PATH:-}" ]; then
		# Ensure directory exists and file is touched to avoid race/permission problems in test harnesses
		mkdir -p "$(dirname "$VPN_SENTINEL_TEST_CAPTURE_PATH")" 2>/dev/null || true
		touch "$VPN_SENTINEL_TEST_CAPTURE_PATH" 2>/dev/null || true
		# Write a compact, single-line JSON payload so tests can parse entries by line.
		if command -v jq >/dev/null 2>&1; then
			printf '%s' "$PAYLOAD" | jq -c . >> "$VPN_SENTINEL_TEST_CAPTURE_PATH" 2>/dev/null || true
		else
			# Fallback: remove newlines to produce a single-line representation
			printf '%s' "$PAYLOAD" | tr '\n' ' ' | sed 's/\s\+/ /g' >> "$VPN_SENTINEL_TEST_CAPTURE_PATH" 2>/dev/null || true
		fi
		return 0
	fi
	if curl -X POST "${SERVER_URL}/keepalive" \
		-H "Content-Type: application/json" \
		${VPN_SENTINEL_API_KEY:+-H "Authorization: Bearer $VPN_SENTINEL_API_KEY"} \
		${CURL_OPTS:+$CURL_OPTS} \
		--max-time "$TIMEOUT" \
		-d "$PAYLOAD" \
		>/dev/null 2>&1; then
		return 0
	else
		return 1
	fi
}
