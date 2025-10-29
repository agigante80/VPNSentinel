"""vpn_sentinel_server package (incremental modularization).

This package starts as a thin compatibility layer that re-exports select
utilities from the legacy `vpn-sentinel-server/vpn-sentinel-server.py` module.
As refactor work progresses, logic should be moved here and imports updated.
"""

from .utils import get_current_time, log_info, log_warn, log_error

__all__ = ["get_current_time", "log_info", "log_warn", "log_error"]
