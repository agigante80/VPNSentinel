"""vpn_sentinel_server package compatibility layer.

This package exposes a stable module-level API so tests and external code that
`import vpn_sentinel_server` can continue to find the legacy module-level
attributes (for example: `requests`, `TELEGRAM_BOT_TOKEN`, `ALLOWED_IPS`,
validation helpers, Flask apps, etc.) while the refactor moves real
implementations into submodules.

Implementation strategy:
- Attempt to import the legacy monolith file located at
  `../vpn-sentinel-server/vpn-sentinel-server.py` and execute it as a module
  under a private name. Then copy its public attributes into this package's
  top-level namespace. This keeps backwards compatibility for tests and
  runtime code that patches attributes on `vpn_sentinel_server`.
"""

from .utils import get_current_time, log_info, log_warn, log_error

# Re-export commonly-used utilities from submodules so top-level attributes
# refer to the exact function objects defined in their modules. Tests expect
# byte-for-byte identical code objects when comparing delegation; assigning
# these references here ensures that.
from . import security as _security
from . import validation as _validation

# Basic utilities
get_current_time = get_current_time
log_info = log_info
log_warn = log_warn
log_error = log_error

# Security helpers (re-export function objects)
check_rate_limit = _security.check_rate_limit
check_ip_whitelist = _security.check_ip_whitelist
log_access = _security.log_access
security_middleware = _security.security_middleware

# Override check_ip_whitelist with a small wrapper that prefers the package
# level ALLOWED_IPS if present (tests patch this value on the package). This
# wrapper intentionally exists only for whitelist behavior; other functions
# are direct re-exports so their code objects remain identical to the
# implementations in their modules.
def check_ip_whitelist(ip: str) -> bool:
	try:
		if 'ALLOWED_IPS' in globals():
			allowed = globals().get('ALLOWED_IPS')
			if not allowed:
				return True
			return ip in allowed
	except Exception:
		pass

	return _security.check_ip_whitelist(ip)

# Validation helpers (re-export function objects)
get_client_ip = _validation.get_client_ip
validate_client_id = _validation.validate_client_id
validate_public_ip = _validation.validate_public_ip
validate_location_string = _validation.validate_location_string

__all__ = [
	"get_current_time",
	"log_info",
	"log_warn",
	"log_error",
	"check_rate_limit",
	"check_ip_whitelist",
	"log_access",
	"security_middleware",
	"get_client_ip",
	"validate_client_id",
	"validate_public_ip",
	"validate_location_string",
]

# For backward compatibility with code/tests that expect the legacy monolith
# module attributes (Flask apps, TELEGRAM_BOT_TOKEN, requests, etc.), try to
# load the monolith and copy any missing attributes into the package
# namespace. Don't overwrite the explicit re-exports above.
import importlib.util
import os
import sys
try:
	monolith_path = os.path.join(os.path.dirname(__file__), '..', 'vpn-sentinel-server', 'vpn-sentinel-server.py')
	monolith_path = os.path.normpath(monolith_path)
	if os.path.exists(monolith_path):
		spec = importlib.util.spec_from_file_location('_vpn_sentinel_server_monolith', monolith_path)
		_monolith = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(_monolith)

		for name in dir(_monolith):
			if name.startswith('_'):
				continue
			if name in globals():
				continue
			globals()[name] = getattr(_monolith, name)
			__all__.append(name)
		globals()['_monolith_module'] = _monolith
except Exception:
	pass
