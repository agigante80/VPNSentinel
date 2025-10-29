import time
import threading

from vpn_sentinel_common.monitor import Monitor


def test_monitor_emits_heartbeats_and_stops():
    received = []
    lock = threading.Lock()

    def cb(hb):
        with lock:
            received.append(hb)

    m = Monitor(component="test", interval=0.1, on_heartbeat=cb)
    assert not m.is_running()
    m.start()
    assert m.is_running()

    # Wait for a few heartbeats
    time.sleep(0.35)

    m.stop()
    assert not m.is_running()

    with lock:
        assert len(received) >= 2
        for hb in received:
            assert isinstance(hb, dict)
            assert hb.get("component") == "test"
            assert "ts" in hb