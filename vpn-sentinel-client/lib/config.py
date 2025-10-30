"""Thin compatibility shim for client config.

This file re-exports `load_config` and `generate_client_id` from
`vpn_sentinel_common.config` when available. When run as a script the shim
supports the `--print-json` flag used by the shell wrapper.
"""
from __future__ import annotations

from typing import Dict, Any

__all__ = ["load_config", "generate_client_id"]

try:
	from vpn_sentinel_common.config import load_config, generate_client_id  # type: ignore
except Exception:
	# Local fallback implementations to keep tests and the shell wrapper working
	import os
	import time
	import random
	import re


	def _sanitize_client_id(cid: str) -> str:
		s = cid.lower()
		s = re.sub(r"[^a-z0-9-]", "-", s)
		s = re.sub(r"-+", "-", s)
		s = s.strip("-")
		return s or "sanitized-client"


	def generate_client_id(env: Dict[str, str]) -> str:
		cid = env.get("VPN_SENTINEL_CLIENT_ID")
		if cid:
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
	import json
	import os

	cfg = load_config(dict(os.environ))
	print(json.dumps(cfg))


if __name__ == "__main__":
	import sys

	if len(sys.argv) > 1 and sys.argv[1] == "--print-json":
		_print_json_from_environ()
	else:
		pass
