"""Utility shims for vpn_sentinel_server.

These functions currently delegate to the legacy `vpn-sentinel-server.py` to
preserve behaviour during migration. Later, move implementations here and
update imports across the codebase.
"""

from typing import Any

# Import from the monolithic server module. Keep imports local to avoid import
# cycles during the incremental refactor.
def _legacy():
    # Load the legacy module by file path to avoid issues with hyphens in package
    # names. This keeps the shim independent of package import semantics.
    import importlib.util
    import importlib.machinery
    import os
    repo_root = os.path.dirname(os.path.dirname(__file__))
    legacy_path = os.path.join(repo_root, 'vpn-sentinel-server', 'vpn-sentinel-server.py')
    spec = importlib.util.spec_from_loader('legacy_vpn_server', importlib.machinery.SourceFileLoader('legacy_vpn_server', legacy_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def get_current_time() -> Any:
    """Return current time via legacy helper."""
    mod = _legacy()
    return mod.get_current_time()

def log_info(component: str, message: str) -> None:
    mod = _legacy()
    return mod.log_info(component, message)

def log_warn(component: str, message: str) -> None:
    mod = _legacy()
    return mod.log_warn(component, message)

def log_error(component: str, message: str) -> None:
    mod = _legacy()
    return mod.log_error(component, message)
