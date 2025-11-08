#!/usr/bin/env bash
# Minimal shell logging shim for vpn-sentinel-client
# Provides log_info, log_warn, log_error used by the client script during startup

log_info() {
    local component="$1"
    local message="$2"
    printf 'INFO [%s] %s\n' "$component" "$message" >&1
}

log_warn() {
    local component="$1"
    local message="$2"
    printf 'WARN [%s] %s\n' "$component" "$message" >&1
}

log_error() {
    local component="$1"
    local message="$2"
    printf 'ERROR [%s] %s\n' "$component" "$message" >&2
}

export -f log_info log_warn log_error >/dev/null 2>&1 || true
