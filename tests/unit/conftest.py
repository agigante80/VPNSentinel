"""Shared fixtures for the unit suite.

The Apprise worker (vpn_sentinel.common.notifications) is one module-level daemon thread with a
bounded queue. Without a reset between tests, a sender that blocks in one test would keep the
worker busy for every later test (alert deliveries would never be processed), and the
`apprise` logger level the worker sets would leak. This autouse fixture gives every test a fresh
worker state, an empty Apprise environment, and the original `apprise` logger level back.
"""

import logging

import pytest

from vpn_sentinel.common import notifications


@pytest.fixture(autouse=True)
def _isolated_notifications(monkeypatch):
    monkeypatch.delenv("VPN_SENTINEL_APPRISE_URLS", raising=False)
    monkeypatch.delenv("VPN_SENTINEL_APPRISE_URLS_FILE", raising=False)
    apprise_logger = logging.getLogger("apprise")
    saved_level = apprise_logger.level
    notifications._reset_for_tests()
    yield
    notifications._reset_for_tests()
    apprise_logger.setLevel(saved_level)
