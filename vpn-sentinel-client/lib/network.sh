#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC2034
# Network helpers for vpn-sentinel-client
# Sourced by vpn-sentinel-client.sh

# get_vpn_info: populate PUBLIC_IP, COUNTRY, CITY, REGION, ORG, VPN_TIMEZONE
get_vpn_info() {
	log_info "vpn-info" "🔍 Gathering VPN information..."

	# Try Python-based shared geolocation shim first if python3 is available.
	if command -v python3 >/dev/null 2>&1; then
		PY_SERVICE="${GEOLOCATION_SERVICE:-auto}"
		PY_OUTPUT=$(python3 -c 'import json,sys
from vpn_sentinel_client.lib.geo_client import main as _m
import vpn_sentinel_client.lib.geo_client as __mod
sys.argv=["geo","--service",__import__("sys").argv[1] if len(__import__("sys").argv)>1 else "auto"]
' 2>/dev/null || true)
		# The above inline call may fail in certain execution contexts; try module runner
		if [ -z "$PY_OUTPUT" ]; then
			PY_OUTPUT=$(python3 -m vpn-sentinel-client.lib.geo_client --service "${GEOLOCATION_SERVICE:-auto}" --timeout "$TIMEOUT" 2>/dev/null || true)
		fi
		if [ -n "$PY_OUTPUT" ]; then
			VPN_INFO="$PY_OUTPUT"
			GEOLOCATION_SOURCE=$(printf '%s' "$VPN_INFO" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("source",""))')
			[ "${DEBUG_ENABLED:-false}" = "true" ] && log_info "vpn-info" "🔍 (py) Raw VPN_INFO: $VPN_INFO"
		fi
	fi

	if [ "${GEOLOCATION_SERVICE:-auto}" = "ipinfo.io" ]; then
		VPN_INFO=$(curl -s --max-time "$TIMEOUT" https://ipinfo.io/json 2>/dev/null || echo '')
		GEOLOCATION_SOURCE="ipinfo.io"
		[ "${DEBUG_ENABLED:-false}" = "true" ] && log_info "vpn-info" "🔍 Raw VPN_INFO: $VPN_INFO"
	elif [ "${GEOLOCATION_SERVICE:-auto}" = "ip-api.com" ]; then
		VPN_INFO=$(curl -s --max-time "$TIMEOUT" http://ip-api.com/json 2>/dev/null || echo '{}')
		GEOLOCATION_SOURCE="ip-api.com"
		[ "${DEBUG_ENABLED:-false}" = "true" ] && log_info "vpn-info" "🔍 Raw VPN_INFO: $VPN_INFO"
	else
		VPN_INFO=$(curl -s --max-time "$TIMEOUT" https://ipinfo.io/json 2>/dev/null || echo '')
		if [ -z "${VPN_INFO}" ] || [ "${VPN_INFO}" = "{}" ]; then
			log_warn "vpn-info" "⚠️ Primary geolocation service (ipinfo.io) failed, trying fallback..."
			VPN_INFO=$(curl -s http://ip-api.com/json 2>/dev/null || echo '{}')
			GEOLOCATION_SOURCE="ip-api.com"
		else
			GEOLOCATION_SOURCE="ipinfo.io"
		fi
		[ "${DEBUG_ENABLED:-false}" = "true" ] && log_info "vpn-info" "🔍 Raw VPN_INFO: $VPN_INFO"
	fi

	log_info "vpn-info" "📡 Using geolocation service: $GEOLOCATION_SOURCE"

	# Use jq to extract fields robustly. jq returns empty string when field missing.
	if command -v jq >/dev/null 2>&1; then
		if [ "$GEOLOCATION_SOURCE" = "ip-api.com" ]; then
			PUBLIC_IP_RAW=$(printf '%s' "$VPN_INFO" | jq -r '.query // empty')
			COUNTRY_RAW=$(printf '%s' "$VPN_INFO" | jq -r '.countryCode // empty')
			CITY_RAW=$(printf '%s' "$VPN_INFO" | jq -r '.city // empty')
			REGION_RAW=$(printf '%s' "$VPN_INFO" | jq -r '.regionName // empty')
			ORG_RAW=$(printf '%s' "$VPN_INFO" | jq -r '.isp // empty')
			VPN_TIMEZONE_RAW=$(printf '%s' "$VPN_INFO" | jq -r '.timezone // empty')
		else
			PUBLIC_IP_RAW=$(printf '%s' "$VPN_INFO" | jq -r '.ip // empty')
			COUNTRY_RAW=$(printf '%s' "$VPN_INFO" | jq -r '.country // empty')
			CITY_RAW=$(printf '%s' "$VPN_INFO" | jq -r '.city // empty')
			REGION_RAW=$(printf '%s' "$VPN_INFO" | jq -r '.region // empty')
			ORG_RAW=$(printf '%s' "$VPN_INFO" | jq -r '.org // empty')
			VPN_TIMEZONE_RAW=$(printf '%s' "$VPN_INFO" | jq -r '.timezone // empty')
		fi
	else
		# Fallback to previous sed-based approach if jq is not available
		VPN_INFO_CLEAN=$(echo "$VPN_INFO" | tr -d '\n' | sed 's/[[:space:]]\+/ /g')
		if [ "$GEOLOCATION_SOURCE" = "ip-api.com" ]; then
			PUBLIC_IP_RAW=$(echo "$VPN_INFO_CLEAN" | sed -n 's/.*"query"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
			COUNTRY_RAW=$(echo "$VPN_INFO_CLEAN" | sed -n 's/.*"countryCode"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
			CITY_RAW=$(echo "$VPN_INFO_CLEAN" | sed -n 's/.*"city"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
			REGION_RAW=$(echo "$VPN_INFO_CLEAN" | sed -n 's/.*"regionName"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
			ORG_RAW=$(echo "$VPN_INFO_CLEAN" | sed -n 's/.*"isp"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
			VPN_TIMEZONE_RAW=$(echo "$VPN_INFO_CLEAN" | sed -n 's/.*"timezone"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
		else
			PUBLIC_IP_RAW=$(echo "$VPN_INFO_CLEAN" | sed -n 's/.*"ip"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
			COUNTRY_RAW=$(echo "$VPN_INFO_CLEAN" | sed -n 's/.*"country"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
			CITY_RAW=$(echo "$VPN_INFO_CLEAN" | sed -n 's/.*"city"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
			REGION_RAW=$(echo "$VPN_INFO_CLEAN" | sed -n 's/.*"region"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
			ORG_RAW=$(echo "$VPN_INFO_CLEAN" | sed -n 's/.*"org"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
			VPN_TIMEZONE_RAW=$(echo "$VPN_INFO_CLEAN" | sed -n 's/.*"timezone"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
		fi
	fi

	PUBLIC_IP=$(sanitize_string "$PUBLIC_IP_RAW")
	COUNTRY=$(sanitize_string "$COUNTRY_RAW")
	CITY=$(sanitize_string "$CITY_RAW")
	REGION=$(sanitize_string "$REGION_RAW")
	ORG=$(sanitize_string "$ORG_RAW")
	VPN_TIMEZONE=$(sanitize_string "$VPN_TIMEZONE_RAW")
}

# get_dns_info: populate DNS_LOC and DNS_COLO
get_dns_info() {
	DNS_INFO=$(curl -s --max-time "$TIMEOUT" https://1.1.1.1/cdn-cgi/trace 2>/dev/null || echo '')
	DNS_LOC_RAW=$(echo "$DNS_INFO" | grep '^loc=' | cut -d'=' -f2)
	DNS_COLO_RAW=$(echo "$DNS_INFO" | grep '^colo=' | cut -d'=' -f2)
	DNS_LOC=$(sanitize_string "$DNS_LOC_RAW")
	DNS_COLO=$(sanitize_string "$DNS_COLO_RAW")
}
