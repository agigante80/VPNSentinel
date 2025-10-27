#!/bin/sh
# Utility helpers for vpn-sentinel-client

json_escape() {
	printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\\"/g'
}

sanitize_string() {
	printf '%s' "$1" | tr -d '\000-\037' | head -c 100
}
