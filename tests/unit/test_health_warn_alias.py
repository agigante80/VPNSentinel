import pytest

from vpn_sentinel_common import health as health_module


def test_component_warn_alias_normalizes_to_degraded():
    components = {"api": {"status": "warn", "details": {}}}
    h = health_module.make_health("degraded", 1, components)
    assert h["components"]["api"]["status"] == "degraded"
    valid, errs = health_module.validate_health(h)
    assert valid, f"unexpected validation errors: {errs}"


def test_component_mixed_case_warn_normalizes():
    components = {"api": {"status": "Warn", "details": {}}}
    h = health_module.make_health("degraded", 2, components)
    assert h["components"]["api"]["status"] == "degraded"
    valid, errs = health_module.validate_health(h)
    assert valid
