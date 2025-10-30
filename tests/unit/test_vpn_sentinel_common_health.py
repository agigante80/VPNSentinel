import json
import time
from datetime import datetime, timezone

import pytest

from vpn_sentinel_common import health as health_module


def test_make_health_and_validate_ok():
    components = {"api": {"status": "ok", "details": {"uptime": "running"}}}
    h = health_module.make_health("ok", 5, components, version="1.2.3")

    assert h["status"] == "ok"
    assert isinstance(h["uptime_seconds"], int)
    assert "timestamp" in h and isinstance(h["timestamp"], str)
    assert "server_time" in h
    assert h["components"]["api"]["status"] == "ok"
    assert h.get("version") == "1.2.3"

    valid, errors = health_module.validate_health(h)
    assert valid, f"unexpected validation errors: {errors}"


def test_make_health_invalid_overall_status():
    components = {"api": {"status": "ok", "details": {}}}
    with pytest.raises(ValueError):
        health_module.make_health("UNKNOWN", 1, components)


def test_component_invalid_status_fails():
    components = {"api": {"status": "bad", "details": {}}}
    with pytest.raises(ValueError):
        health_module.make_health("ok", 1, components)


def test_validate_health_detects_errors():
    bad = {"status": "broken", "uptime_seconds": -1}
    valid, errors = health_module.validate_health(bad)
    assert not valid
    assert any("invalid status" in e or "uptime_seconds" in e or "missing key" in e for e in errors)


def test_sample_health_ok_contains_defaults():
    s = health_module.sample_health_ok(version="vtest")
    ok, errs = health_module.validate_health(s)
    assert ok
    assert s.get("version") == "vtest"
