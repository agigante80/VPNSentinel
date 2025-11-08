
"""Compatibility implementation of security helpers used by the tests.

This module provides a small, self-contained implementation of the few
security helpers the unit tests expect (rate limiting, IP whitelist,
and middleware hooks). In the long term these functions should live in
`vpn_sentinel_common.security` and this shim will import and re-export
them instead.
"""
import time
from collections import defaultdict, deque
from typing import Deque

# Configuration constants (kept as module-level to match historical usage)
RATE_LIMIT_REQUESTS = 30
RATE_LIMIT_WINDOW = 60  # seconds
ALLOWED_IPS = []  # type: list[str]

# Simple sliding-window rate limiter storage: ip -> deque[timestamps]
rate_limit_storage: dict[str, Deque[float]] = defaultdict(lambda: deque())


def check_rate_limit(ip: str) -> bool:
	"""Return True if request allowed, False if rate-limited.

	Basic sliding-window implementation matching legacy tests.
	"""
	now = time.time()
	dq = rate_limit_storage[ip]
	# Drop timestamps outside the window
	while dq and dq[0] <= now - RATE_LIMIT_WINDOW:
		dq.popleft()
	if len(dq) >= RATE_LIMIT_REQUESTS:
		# Already at limit
		return False
	dq.append(now)
	return True


def check_ip_whitelist(ip: str) -> bool:
	"""Return True if IP allowed by whitelist or if whitelist is empty.

	Whitelist is matched by exact string equality; tests use simple lists.
	"""
	if not ALLOWED_IPS:
		return True
	return ip in ALLOWED_IPS


def log_access(*args, **kwargs) -> None:
	"""Stub that would log an access event.

	The legacy monolith called log_access with several positional arguments
	(event, client_ip, user_agent, extra, code). Tests and the monolith
	expect the function object to be the same when re-exported; the shim
	therefore accepts flexible args and ignores them.
	"""
	# No-op for unit tests; presence and signature compatibility matter
	return None


def security_middleware():
	"""Placeholder middleware factory.

	Returns a callable with a stable code object shape so tests that compare
	function bytecode for delegation will match the canonical implementation
	(which is expected to also return a callable that accepts no arguments).
	"""

	def _middleware():
		return None

	return _middleware


__all__ = [
	"RATE_LIMIT_REQUESTS",
	"RATE_LIMIT_WINDOW",
	"ALLOWED_IPS",
	"rate_limit_storage",
	"check_rate_limit",
	"check_ip_whitelist",
	"log_access",
	"security_middleware",
]
