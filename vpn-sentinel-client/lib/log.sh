#!/usr/bin/env bash
# Minimal compatibility shim for log functions used by the client script and tests.
# This file exists only as a small fallback while the project migrates logging to
# the Python `lib/log.py` shim. Keep behavior intentionally simple and stable
# so unit tests can assert on output.

log_message() {
    # $1 = LEVEL, $2 = COMPONENT, $3.. = MESSAGE
    local level="$1" component="$2"
    shift 2
    local message="$*"
    # Print a compact, human-friendly message similar to original shell helper
    printf '%s %s\n' "${component:+[${component}] }" "${message}"
}

log_info() {
    log_message "INFO" "$@"
}

log_warn() {
    log_message "WARN" "$@"
}

log_error() {
    log_message "ERROR" "$@" >&2
}

export -f log_message log_info log_warn log_error >/dev/null 2>&1 || true
