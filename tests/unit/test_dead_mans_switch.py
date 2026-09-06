"""Tests for dead-man's-switch alerting (issue #82).

Covers the two alerts added to close the "client stops sending keepalives and nothing
is said" gap:

- telegram.notify_clients_silent(): per-client silence alert, batched for a whole sweep.
- telegram.notify_no_clients(): fleet-empty catch-all, latched so it fires once per
  genuine transition to zero clients (not once per 60-second sweep).

These tests exercise vpn_sentinel.common.api_routes._run_cleanup_sweep() directly rather
than the surrounding infinite loop/sleep in cleanup_stale_clients(), and patch the
`telegram` module reference inside api_routes so no network call is made.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from vpn_sentinel.common import api_routes
from vpn_sentinel.common.api_routes import api_app, client_status, _client_first_seen, _run_cleanup_sweep


def _iso_minutes_ago(minutes: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


@pytest.fixture
def clean_state():
    """Reset all cleanup-related shared state before and after each test.

    api_routes._fleet_empty_reported is reset to True (its value at import time) rather
    than False, so a test that forgets to set it up explicitly fails safe the same way a
    freshly started server would.
    """
    client_status.clear()
    _client_first_seen.clear()
    api_routes._fleet_empty_reported = True
    yield
    client_status.clear()
    _client_first_seen.clear()
    api_routes._fleet_empty_reported = True


@pytest.fixture
def flask_client():
    api_app.config["TESTING"] = True
    with api_app.test_client() as c:
        yield c


class _InjectOnceLock:
    """Wraps the real client_status_lock; on its Nth `with` use, runs an injected callback
    right after acquiring, before the caller's own critical section runs.

    Used to deterministically simulate a keepalive that grabs client_status_lock and
    writes a fresh record in the exact window a real concurrent Flask request thread could
    land in: between the cleanup sweep's earlier (now-released) lock uses and its next one.
    """

    def __init__(self, real_lock, trigger_on_use, inject):
        self._real_lock = real_lock
        self._trigger_on_use = trigger_on_use
        self._inject = inject
        self._use_count = 0

    def __enter__(self):
        self._real_lock.acquire()
        self._use_count += 1
        if self._use_count == self._trigger_on_use:
            self._inject()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._real_lock.release()
        return False


@patch("vpn_sentinel.common.api_routes.telegram")
def test_single_client_silent_produces_one_alert_naming_it(mock_telegram, clean_state):
    """One client going silent produces exactly one alert naming it."""
    client_status["office-vpn-primary"] = {"last_seen": _iso_minutes_ago(45)}

    _run_cleanup_sweep()

    mock_telegram.notify_clients_silent.assert_called_once()
    (clients_arg,), _ = mock_telegram.notify_clients_silent.call_args
    assert len(clients_arg) == 1
    client_id, minutes_silent = clients_arg[0]
    assert client_id == "office-vpn-primary"
    assert 44 <= minutes_silent <= 46

    # The fleet-empty alert must not fire in the same sweep: it is checked before the
    # removal loop runs, while the dict is still non-empty.
    mock_telegram.notify_no_clients.assert_not_called()

    # The client was actually removed.
    assert "office-vpn-primary" not in client_status
    assert "office-vpn-primary" not in _client_first_seen


@patch("vpn_sentinel.common.api_routes.telegram")
def test_client_alive_again_before_removal_is_not_deleted_or_reported(mock_telegram, clean_state):
    """A client that sends a fresh keepalive in the window between being snapshotted as
    stale and its removal executing must NOT be deleted and must NOT be reported as
    silent, even though it looked stale when the sweep started.

    The race: staleness is computed outside client_status_lock against a snapshot, then
    the removal loop re-acquires the lock per client. A keepalive can land, under the same
    lock, in between. This is simulated deterministically with _InjectOnceLock: on the
    removal loop's lock acquisition for this client, a "concurrent keepalive" write is
    injected before the removal code's own staleness re-check runs.
    """
    client_status["flaky-client"] = {"last_seen": _iso_minutes_ago(45)}
    _client_first_seen.add("flaky-client")
    fresh_last_seen = _iso_minutes_ago(0)

    def _simulate_concurrent_keepalive():
        # Mirrors keepalive()'s own behavior: replace with a brand new dict under the lock.
        client_status["flaky-client"] = {"last_seen": fresh_last_seen}

    # Use count 2: the 1st use is the fleet-empty check at the top of the sweep; the 2nd is
    # this client's removal-check-and-delete critical section.
    injecting_lock = _InjectOnceLock(
        api_routes.client_status_lock, trigger_on_use=2, inject=_simulate_concurrent_keepalive
    )

    with patch.object(api_routes, "client_status_lock", injecting_lock):
        _run_cleanup_sweep()

    # Not deleted: the fresh record written "concurrently" is still there, untouched.
    assert client_status["flaky-client"]["last_seen"] == fresh_last_seen
    assert "flaky-client" in _client_first_seen

    # Not reported as silent: a client that is currently alive must never appear in the
    # alert batch, and with nothing else stale, notify_clients_silent must not be called
    # at all.
    mock_telegram.notify_clients_silent.assert_not_called()


@patch("vpn_sentinel.common.api_routes.telegram")
def test_three_clients_silent_in_one_sweep_produce_one_batched_message(mock_telegram, clean_state):
    """Several clients going silent in the same sweep produce ONE message, not one each."""
    for i in range(3):
        client_status[f"client-{i}"] = {"last_seen": _iso_minutes_ago(40)}
        _client_first_seen.add(f"client-{i}")

    _run_cleanup_sweep()

    mock_telegram.notify_clients_silent.assert_called_once()
    (clients_arg,), _ = mock_telegram.notify_clients_silent.call_args
    assert {client_id for client_id, _ in clients_arg} == {"client-0", "client-1", "client-2"}
    assert client_status == {}
    assert _client_first_seen == set()


@patch("vpn_sentinel.common.api_routes.telegram")
def test_fleet_empty_alert_fires_when_dict_already_empty_and_latch_clear(mock_telegram, clean_state):
    """The fleet-empty alert fires on a sweep that observes an already-empty dict, as long
    as the latch is clear (i.e. a client had registered since the last time the alert
    fired). This exercises the latch-flip itself, not the live present-to-empty transition
    caused by a sweep's own removals: that is covered by
    test_fleet_empty_alert_fires_again_after_reconnect_then_silent_again below."""
    api_routes._fleet_empty_reported = False
    client_status.clear()

    _run_cleanup_sweep()

    mock_telegram.notify_no_clients.assert_called_once()
    assert api_routes._fleet_empty_reported is True


@patch("vpn_sentinel.common.api_routes.telegram")
def test_neither_alert_repeats_on_next_sweep_while_latch_state_unchanged(mock_telegram, clean_state):
    """Once each alert has fired, a following sweep must not fire either alert again, as
    long as the latch state that gates each alert stays unchanged. Note client_status
    itself does NOT stay the same across the two sweeps here: the first sweep's own
    removal empties it. What stays constant, and is what this test asserts on, is the
    fleet-empty latch (already True throughout) and the absence of any new stale client to
    report."""
    api_routes._fleet_empty_reported = True  # a fleet-empty alert was already reported earlier
    client_status["stale-client"] = {"last_seen": _iso_minutes_ago(50)}

    _run_cleanup_sweep()
    mock_telegram.notify_clients_silent.assert_called_once()
    mock_telegram.notify_no_clients.assert_not_called()

    # client_status is now empty (the stale client was removed by the sweep above) and the
    # fleet-empty latch is still True. A second sweep must not produce any new alert calls.
    _run_cleanup_sweep()

    mock_telegram.notify_clients_silent.assert_called_once()
    mock_telegram.notify_no_clients.assert_not_called()


@patch("vpn_sentinel.common.api_routes.telegram")
def test_fresh_start_with_empty_client_status_does_not_fire_fleet_empty_alert(mock_telegram, clean_state):
    """A freshly started server has an empty client_status but has never seen a client, so
    the fleet-empty latch starts True (already-reported) and must not alert."""
    assert client_status == {}
    assert api_routes._fleet_empty_reported is True  # set by the clean_state fixture,
    # mirroring the module-level default established at import time.

    _run_cleanup_sweep()

    mock_telegram.notify_no_clients.assert_not_called()


@patch("vpn_sentinel.common.api_routes.telegram")
@patch("vpn_sentinel.common.api_routes.get_cached_server_ip")
def test_fleet_empty_alert_fires_again_after_reconnect_then_silent_again(
    mock_server_ip, mock_telegram, clean_state, flask_client
):
    """After a fleet-empty alert has fired, a client reconnecting and then going silent
    again must be able to trigger a fresh fleet-empty alert (the latch must clear on
    registration, not stay latched forever)."""
    mock_server_ip.return_value = "203.0.113.9"
    api_routes._fleet_empty_reported = True  # a "no clients" alert was already sent once

    payload = {
        "client_id": "reconnecting-client",
        "public_ip": "198.51.100.7",
        "city": "Test City",
        "region": "Test Region",
        "country": "US",
        "provider": "TestISP",
        "timezone": "UTC",
    }
    response = flask_client.post("/api/v1/keepalive", json=payload)
    assert response.status_code == 200

    # Registering a client must clear the latch.
    assert api_routes._fleet_empty_reported is False

    # The client now goes silent and gets swept away.
    client_status["reconnecting-client"]["last_seen"] = _iso_minutes_ago(60)
    _run_cleanup_sweep()

    mock_telegram.notify_clients_silent.assert_called_once()
    # Not yet: the empty check runs before the removal loop, so this sweep still saw a
    # non-empty dict at the top.
    mock_telegram.notify_no_clients.assert_not_called()

    # Next sweep: the dict is now empty and the latch was cleared by the reconnect, so the
    # fleet-empty alert can fire again.
    _run_cleanup_sweep()

    mock_telegram.notify_no_clients.assert_called_once()


@patch("vpn_sentinel.common.api_routes.telegram")
def test_unparseable_last_seen_does_not_permanently_suppress_fleet_empty_alert(mock_telegram, clean_state):
    """A client whose last_seen cannot be parsed must not be skipped forever.

    Before the fix, the ValueError/AttributeError branch did `continue`, leaving the
    client in client_status permanently: client_status could never become empty again, so
    the fleet-empty latch could never re-fire. This client is now treated as stale (as of
    right now) instead, so it flows through the normal removal + alert path like any other
    stale client and the dict empties out.
    """
    client_status["corrupted-client"] = {"last_seen": "not-a-real-timestamp"}
    _client_first_seen.add("corrupted-client")
    api_routes._fleet_empty_reported = False

    # First sweep: the corrupted client is treated as stale right now and removed/alerted.
    _run_cleanup_sweep()

    assert client_status == {}
    assert "corrupted-client" not in _client_first_seen
    mock_telegram.notify_clients_silent.assert_called_once()
    (clients_arg,), _ = mock_telegram.notify_clients_silent.call_args
    assert clients_arg[0][0] == "corrupted-client"
    # This sweep's top-of-sweep emptiness check ran before the removal, so it still saw a
    # non-empty dict and must not have fired the fleet-empty alert yet.
    mock_telegram.notify_no_clients.assert_not_called()

    # Second sweep: client_status is genuinely empty now and the latch is clear, so the
    # fleet-empty alert is reachable and fires. This is the behaviour that was permanently
    # broken before the fix: with the old `continue`, client_status would still contain
    # "corrupted-client" here and this alert would never fire.
    _run_cleanup_sweep()

    mock_telegram.notify_no_clients.assert_called_once()
    assert api_routes._fleet_empty_reported is True


@patch("vpn_sentinel.common.api_routes.telegram")
def test_unparseable_last_seen_alongside_healthy_client_does_not_block_its_removal(mock_telegram, clean_state):
    """A corrupted client is removed and reported even when other clients are healthy."""
    client_status["healthy-client"] = {"last_seen": _iso_minutes_ago(0)}
    client_status["corrupted-client"] = {"last_seen": "garbage"}
    _client_first_seen.update({"healthy-client", "corrupted-client"})

    _run_cleanup_sweep()

    assert "corrupted-client" not in client_status
    assert "healthy-client" in client_status
    mock_telegram.notify_clients_silent.assert_called_once()
    (clients_arg,), _ = mock_telegram.notify_clients_silent.call_args
    assert [c[0] for c in clients_arg] == ["corrupted-client"]
