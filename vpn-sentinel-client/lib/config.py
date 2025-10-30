"""Thin compatibility shim for client config.

This file exists to keep tests and legacy callers that import the file path
working while the canonical implementation lives in
`vpn_sentinel_common.config`.
"""
from __future__ import annotations

try:
    from vpn_sentinel_common.config import load_config, generate_client_id  # type: ignore
except Exception:
    # Fallback implementations if the canonical package is not available.
    import os
    from typing import Dict, Any


    def generate_client_id(env: Dict[str, str]) -> str:
        # Minimal fallback behavior (keeps tests simple)
        return env.get("VPN_SENTINEL_CLIENT_ID", "fallback-client")


    def load_config(env: Dict[str, str]) -> Dict[str, Any]:
        # Very small fallback matching a subset of canonical behavior
        api_base = env.get("VPN_SENTINEL_URL", "http://your-server-url:5000")
        api_path = env.get("VPN_SENTINEL_API_PATH", "/api/v1")
        if not api_path.startswith("/"):
            api_path = "/" + api_path
        server_url = f"{api_base}{api_path}"
        return {
            "server_url": server_url,
            "client_id": generate_client_id(env),
            "timeout": int(env.get("VPN_SENTINEL_TIMEOUT", "30")),
            "interval": int(env.get("VPN_SENTINEL_INTERVAL", "300")),
            "api_path": api_path,
            "tls_cert_path": env.get("VPN_SENTINEL_TLS_CERT_PATH", ""),
            "debug": env.get("VPN_SENTINEL_DEBUG", "false").lower() == "true",
        }
"""Thin client shim: re-export canonical config helpers from vpn_sentinel_common.

This module intentionally re-exports the canonical functions from
`vpn_sentinel_common.config`. During migration we keep this file to avoid
changing import paths across the codebase; it is expected to be removed once
all callers import `vpn_sentinel_common.config` directly.
"""
from __future__ import annotations

from typing import Dict, Any

__all__ = ["load_config", "generate_client_id"]

# Prefer importing the canonical implementation. When running tests locally
# (outside the CI/docker build), the top-level package may not be installed
# into the environment. Provide a light-weight fallback so the CLI wrapper
# used by the shell script continues to work and returns the expected JSON.
try:
	from vpn_sentinel_common.config import load_config, generate_client_id  # type: ignore
except Exception:
	# Fallback implementations mirror the behavior of the canonical module
	# but avoid external dependencies so unit/integration tests running in
	# the repository root continue to behave.
	import os
	import time
	import random
	import re
	from typing import Dict, Any


	def _sanitize_client_id(cid: str) -> str:
		s = cid.lower()
		s = re.sub(r"[^a-z0-9-]", "-", s)
		s = re.sub(r"-+", "-", s)
		s = s.strip("-")
		return s or "sanitized-client"


	def generate_client_id(env: Dict[str, str]) -> str:
		cid = env.get("VPN_SENTINEL_CLIENT_ID")
		if cid:
			# match behavior of canonical sanitizer: preserve lower-case alnum and hyphen
			if any(c for c in cid if not (c.islower() or c.isdigit() or c == "-")):
				return _sanitize_client_id(cid)
			return cid
		ts = str(int(time.time()))
		ts = ts[-7:]
		rand = f"{random.randint(100000,999999):06d}"
		return f"vpn-client-{ts}{rand}"


	def load_config(env: Dict[str, str]) -> Dict[str, Any]:
		api_base = env.get("VPN_SENTINEL_URL", "http://your-server-url:5000")
		api_path = env.get("VPN_SENTINEL_API_PATH", "/api/v1") or "/api/v1"
		if not api_path.startswith("/"):
			api_path = "/" + api_path
		server_url = f"{api_base}{api_path}"

		def _safe_int(val, default):
			try:
				return int(val)
			except Exception:
				return default

		timeout = _safe_int(env.get("VPN_SENTINEL_TIMEOUT", env.get("TIMEOUT", 30)), 30)
		interval = _safe_int(env.get("VPN_SENTINEL_INTERVAL", env.get("INTERVAL", 300)), 300)
		client_id = generate_client_id(env)

		tls_cert_path = env.get("VPN_SENTINEL_TLS_CERT_PATH", "")
		allow_insecure = env.get("VPN_SENTINEL_ALLOW_INSECURE", "false").lower() == "true"
		debug = env.get("VPN_SENTINEL_DEBUG", "false").lower() == "true"

		version = env.get("VERSION") or (f"1.0.0-dev-{env.get('COMMIT_HASH')}" if env.get('COMMIT_HASH') else "1.0.0-dev")

		return {
			"version": version,
			"api_base": api_base,
			"api_path": api_path,
			"server_url": server_url,
			"is_https": api_base.startswith("https://"),
			"timeout": timeout,
			"interval": interval,
			"client_id": client_id,
			"tls_cert_path": tls_cert_path,
			"allow_insecure": allow_insecure,
			"debug": debug,
		}


def _print_json_from_environ() -> None:
	"""Helper used when this shim is executed as a script by the shell.

	The legacy shell entrypoint calls this module as a script with
	`--print-json` expecting a JSON object containing configuration keys.
	Keep a tiny wrapper that calls the canonical implementation and
	emits JSON to stdout so runtime behavior is preserved during
	the migration.
	"""
	import json
	import os

	cfg = load_config(dict(os.environ))
	print(json.dumps(cfg))


if __name__ == "__main__":
	import sys

	# Only support the minimal compatibility flag the shell uses.
	if len(sys.argv) > 1 and sys.argv[1] == "--print-json":
		_print_json_from_environ()
	else:
		# When executed without recognized args, be a no-op to avoid
		# changing other tooling that may import this module as a script.
		pass
