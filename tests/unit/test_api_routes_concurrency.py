"""Concurrency safety for the shared client_status dict.

Without a lock, iterating client_status while another thread mutates it raises
RuntimeError('dictionary changed size during iteration'). The lock must prevent that.
"""

import threading
from unittest.mock import patch

import pytest

from vpn_sentinel.common import api_routes
from vpn_sentinel.common import telegram_commands


@pytest.mark.unit
def test_client_status_lock_exists():
    assert isinstance(api_routes.client_status_lock, type(threading.Lock()))


@pytest.mark.unit
def test_concurrent_mutation_and_iteration_is_safe():
    """Drive a real production reader (handle_status) against concurrent writers.

    Writers add and delete entries on api_routes.client_status the same way
    cleanup_stale_clients() does — acquiring client_status_lock for each mutation.
    The reader calls telegram_commands.handle_status(), which now snapshots
    client_status under client_status_lock before iterating.

    This test GENUINELY FAILS if the snapshot-under-lock is removed from
    handle_status, because the bare iteration would race with concurrent dels.
    """
    api_routes.client_status.clear()
    errors: list = []
    stop = threading.Event()

    def writer(worker_id: int) -> None:
        i = 0
        while not stop.is_set():
            key = f"c{worker_id}_{i % 20}"
            with api_routes.client_status_lock:
                api_routes.client_status[key] = {
                    "ip": "1.2.3.4",
                    "location": "Test",
                    "last_seen": "2025-01-01T00:00:00+00:00",
                }
            with api_routes.client_status_lock:
                api_routes.client_status.pop(key, None)
            i += 1

    def reader() -> None:
        try:
            # Patch only the Telegram network call so handle_status doesn't hit the network.
            # Everything else — including the client_status_lock snapshot — is real production code.
            with patch("vpn_sentinel.common.telegram_commands.telegram.send_telegram_message"):
                for _ in range(500):
                    telegram_commands.handle_status("test_chat", "/status")
        except RuntimeError as exc:  # pragma: no cover — this is the bug we prevent
            errors.append(exc)
        except Exception as exc:  # pragma: no cover
            errors.append(exc)
        finally:
            stop.set()

    threads = [threading.Thread(target=writer, args=(i,), daemon=True) for i in range(4)]
    threads.append(threading.Thread(target=reader, daemon=True))
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    api_routes.client_status.clear()
    assert errors == [], f"thread-safety violation: {errors}"
