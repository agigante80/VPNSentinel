import importlib
import vpn_sentinel_server.security as sec_pkg
import vpn_sentinel_server.validation as val_pkg

import vpn_sentinel_server

# Import monolith module
import vpn_sentinel_server as server_pkg_shim


def test_log_access_delegation():
    # The monolith exposes log_access via its top-level name which should be the same as the package impl
    import vpn_sentinel_server.security as sec
    from vpn_sentinel_server import security as sec_alias
    # If monolith re-exported names, they will be attributes in the top-level module (vpn_sentinel_server)
    assert hasattr(server_pkg_shim, 'log_access')
    assert server_pkg_shim.log_access.__code__.co_code == sec.log_access.__code__.co_code


def test_security_middleware_delegation():
    assert hasattr(server_pkg_shim, 'security_middleware')
    assert server_pkg_shim.security_middleware.__code__.co_code == sec_pkg.security_middleware.__code__.co_code


def test_validation_get_client_ip_delegation():
    assert hasattr(server_pkg_shim, 'get_client_ip')
    assert server_pkg_shim.get_client_ip.__code__.co_code == val_pkg.get_client_ip.__code__.co_code


def test_rate_limit_function_delegation():
    assert hasattr(server_pkg_shim, 'check_rate_limit')
    assert server_pkg_shim.check_rate_limit.__code__.co_code == sec_pkg.check_rate_limit.__code__.co_code
