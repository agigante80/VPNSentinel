"""Concurrency safety for the shared client_status dict.

Without a lock, iterating client_status while another thread mutates it raises
RuntimeError('dictionary changed size during iteration'). The lock must prevent that.
"""

import threading

import pytest

from vpn_sentinel.common import api_routes


@pytest.mark.unit
def test_client_status_lock_exists():
    assert isinstance(api_routes.client_status_lock, type(threading.Lock()))


@pytest.mark.unit
def test_concurrent_mutation_and_iteration_is_safe():
    api_routes.client_status.clear()
    errors = []
    stop = threading.Event()

    def writer():
        i = 0
        while not stop.is_set():
            with api_routes.client_status_lock:
                api_routes.client_status[f"c{i % 50}"] = {"ip": "1.2.3.4", "last_seen": i}
            i += 1

    def reader():
        try:
            for _ in range(2000):
                with api_routes.client_status_lock:
                    # snapshot under the lock, then "use" outside
                    snapshot = dict(api_routes.client_status)
                _ = list(snapshot.items())
        except RuntimeError as exc:  # pragma: no cover - this is the bug we prevent
            errors.append(exc)
        finally:
            stop.set()

    ts = [threading.Thread(target=writer) for _ in range(4)] + [threading.Thread(target=reader)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(timeout=10)
    api_routes.client_status.clear()
    assert errors == [], f"thread-safety violation: {errors}"
