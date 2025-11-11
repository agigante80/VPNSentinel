"""Unit tests for vpn_sentinel_common.monitor module."""
import time
import threading
import json
from unittest.mock import Mock

from vpn_sentinel_common.monitor import Monitor


def test_monitor_emits_heartbeats_and_stops():
    """Test monitor emits heartbeats and can be stopped."""
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


def test_monitor_heartbeat_json():
    """Test heartbeat_json returns valid JSON string."""
    m = Monitor(component="json-test")
    
    result = m.heartbeat_json()
    assert isinstance(result, str)
    
    # Should be valid JSON
    data = json.loads(result)
    assert data['component'] == 'json-test'
    assert data['status'] == 'ok'
    assert 'ts' in data
    assert 'info' in data


def test_monitor_callback_exception_handled():
    """Test monitor continues running if callback raises exception."""
    callback = Mock(side_effect=Exception('Callback error'))
    m = Monitor(interval=0.1, on_heartbeat=callback)
    
    # Should not crash despite callback raising exception
    m.start()
    time.sleep(0.25)
    m.stop()
    
    # Callback should have been called despite exceptions
    assert callback.call_count >= 1


def test_monitor_start_twice_no_duplicate():
    """Test starting monitor twice doesn't create duplicate threads."""
    callback = Mock()
    m = Monitor(interval=0.1, on_heartbeat=callback)
    
    m.start()
    time.sleep(0.05)
    
    # Start again - should be ignored
    m.start()
    time.sleep(0.15)
    
    m.stop()
    
    # Should have reasonable number of calls (not doubled)
    assert callback.call_count < 10


def test_monitor_no_callback():
    """Test monitor works without callback."""
    m = Monitor(interval=0.1, on_heartbeat=None)
    
    # Should not crash
    m.start()
    time.sleep(0.15)
    m.stop()


def test_monitor_custom_interval():
    """Test monitor respects custom interval."""
    callback = Mock()
    m = Monitor(interval=1.0, on_heartbeat=callback)
    
    m.start()
    time.sleep(0.5)  # Less than one interval
    m.stop()
    
    # Should have 0-1 calls (since interval is 1 second)
    assert callback.call_count <= 1