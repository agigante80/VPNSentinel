#!/usr/bin/env bash
# shellcheck shell=bash
# Logging library for VPN Sentinel client
# Sourced by vpn-sentinel-client.sh

log_message() {
	local level="$1"
	local component="$2"
	local message="$3"
	local timestamp
	timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
	echo "${timestamp} ${level} [${component}] ${message}"
}

log_info() {
	log_message "INFO" "$1" "$2"
}

log_error() {
	log_message "ERROR" "$1" "$2"
}

log_warn() {
	log_message "WARN" "$1" "$2"
}
