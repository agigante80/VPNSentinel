"""Deprecated validation shim delegating to vpn_sentinel_common.validation."""
import warnings

warnings.warn("vpn_sentinel_server.validation is deprecated; import from vpn_sentinel_common.validation instead", DeprecationWarning)

from vpn_sentinel_common.validation import (
    get_client_ip,
    validate_client_id,
    validate_public_ip,
    validate_location_string,
)  # noqa: E402

__all__ = [
    "get_client_ip",
    "validate_client_id",
    "validate_public_ip",
    "validate_location_string",
]
