"""Re-export security helpers from canonical package.

This module is deprecated; import from vpn_sentinel_common.security instead.
"""
import warnings

warnings.warn(
    "vpn_sentinel_server.security is deprecated; import from vpn_sentinel_common.security instead",
    DeprecationWarning,
)

import vpn_sentinel_common.security
import sys

sys.modules[__name__] = vpn_sentinel_common.security
