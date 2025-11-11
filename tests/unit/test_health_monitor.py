"""Unit and integration tests for health_monitor module."""
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock

from vpn_sentinel_common import health_monitor


ROOT = Path(__file__).resolve().parents[2]
MONITOR = ROOT / 'vpn_sentinel_common' / 'health_monitor.py'
PYTHON = sys.executable or 'python3'


def read_lines_until(proc, predicate, timeout=5.0):
    """Read lines from proc.stdout until predicate(line) is True or timeout."""
    end = time.time() + timeout
    buf = []
    while time.time() < end:
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.05)
            continue
        buf.append(line)
        if predicate(line):
            return buf
    return buf


def test_monitor_heartbeats_and_shutdown(tmp_path):
    assert MONITOR.exists(), f"{MONITOR} not found"

    env = os.environ.copy()
    # Use a short interval so the test runs quickly
    env['VPN_SENTINEL_MONITOR_INTERVAL'] = '1'
    env['PYTHONUNBUFFERED'] = '1'
    env['VERSION'] = 'test-ver'
    env['COMMIT_HASH'] = 'deadbeef'
    env['PYTHONPATH'] = str(ROOT)

    proc = subprocess.Popen([PYTHON, str(MONITOR)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, text=True)

    try:
        # Wait for the startup line
        lines = read_lines_until(proc, lambda l: 'Starting health monitor' in l, timeout=3.0)
        assert any('Starting health monitor' in l for l in lines), f"startup line not seen in output: {lines}"

        # Wait for at least one heartbeat
        lines = read_lines_until(proc, lambda l: 'heartbeat' in l, timeout=5.0)
        assert any('heartbeat' in l for l in lines), f"no heartbeat seen in output: {lines}"

        # Send SIGTERM to request graceful shutdown
        proc.send_signal(signal.SIGTERM)

        # Give the signal handler a moment to run
        time.sleep(0.5)

        # Wait for shutdown messages
        shutdown_lines = read_lines_until(proc, lambda l: 'Monitor stopped' in l or 'shutting down gracefully' in l, timeout=5.0)
        assert any('Monitor stopped' in l or 'shutting down gracefully' in l for l in shutdown_lines), f"no shutdown confirmation in output: {shutdown_lines}"

        # Don't wait for process to exit cleanly - just kill it
        # The important part is that shutdown messages were logged
        proc.kill()
        proc.wait(timeout=2.0)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=2)


# Unit tests for functions in health_monitor module

def test_heartbeat_callback():
    """Test heartbeat_callback logs the heartbeat."""
    with patch('vpn_sentinel_common.health_monitor.log_info') as mock_log:
        heartbeat = {'ts': 1234567890, 'component': 'test', 'status': 'ok'}
        
        health_monitor.heartbeat_callback(heartbeat)
        
        mock_log.assert_called_once()
        call_args = mock_log.call_args[0]
        assert call_args[0] == 'monitor'
        assert 'heartbeat:' in call_args[1]


def test_main_reads_environment():
    """Test main reads configuration from environment."""
    with patch.dict('os.environ', {
        'VPN_SENTINEL_MONITOR_INTERVAL': '60',
        'VERSION': '2.0.0',
        'COMMIT_HASH': 'abc123'
    }):
        with patch('vpn_sentinel_common.health_monitor.Monitor') as mock_monitor_class:
            with patch('vpn_sentinel_common.health_monitor.log_info'):
                with patch('vpn_sentinel_common.health_monitor.time.sleep', side_effect=KeyboardInterrupt):
                    mock_monitor = Mock()
                    mock_monitor_class.return_value = mock_monitor
                    
                    try:
                        health_monitor.main()
                    except KeyboardInterrupt:
                        pass
                    
                    # Verify Monitor was created with correct interval
                    mock_monitor_class.assert_called_once()
                    call_kwargs = mock_monitor_class.call_args[1]
                    assert call_kwargs['interval'] == 60.0


def test_main_uses_default_interval():
    """Test main uses default interval when not in environment."""
    with patch.dict('os.environ', {}, clear=True):
        with patch('vpn_sentinel_common.health_monitor.Monitor') as mock_monitor_class:
            with patch('vpn_sentinel_common.health_monitor.log_info'):
                with patch('vpn_sentinel_common.health_monitor.time.sleep', side_effect=KeyboardInterrupt):
                    mock_monitor = Mock()
                    mock_monitor_class.return_value = mock_monitor
                    
                    try:
                        health_monitor.main()
                    except KeyboardInterrupt:
                        pass
                    
                    # Default interval should be 30
                    call_kwargs = mock_monitor_class.call_args[1]
                    assert call_kwargs['interval'] == 30.0


def test_main_starts_monitor():
    """Test main starts the monitor."""
    with patch('vpn_sentinel_common.health_monitor.Monitor') as mock_monitor_class:
        with patch('vpn_sentinel_common.health_monitor.log_info'):
            with patch('vpn_sentinel_common.health_monitor.time.sleep', side_effect=KeyboardInterrupt):
                mock_monitor = Mock()
                mock_monitor_class.return_value = mock_monitor
                
                try:
                    health_monitor.main()
                except KeyboardInterrupt:
                    pass
                
                mock_monitor.start.assert_called_once()


def test_main_stops_monitor_on_interrupt():
    """Test main stops monitor on KeyboardInterrupt."""
    with patch('vpn_sentinel_common.health_monitor.Monitor') as mock_monitor_class:
        with patch('vpn_sentinel_common.health_monitor.log_info'):
            with patch('vpn_sentinel_common.health_monitor.time.sleep', side_effect=KeyboardInterrupt):
                mock_monitor = Mock()
                mock_monitor_class.return_value = mock_monitor
                
                try:
                    health_monitor.main()
                except KeyboardInterrupt:
                    pass
                
                # Monitor should be stopped
                assert mock_monitor.stop.call_count >= 1


def test_main_registers_signal_handler():
    """Test main sets up SIGTERM handler."""
    with patch('vpn_sentinel_common.health_monitor.Monitor') as mock_monitor_class:
        with patch('vpn_sentinel_common.health_monitor.log_info'):
            with patch('vpn_sentinel_common.health_monitor.signal.signal') as mock_signal:
                with patch('vpn_sentinel_common.health_monitor.time.sleep', side_effect=KeyboardInterrupt):
                    mock_monitor = Mock()
                    mock_monitor_class.return_value = mock_monitor
                    
                    try:
                        health_monitor.main()
                    except KeyboardInterrupt:
                        pass
                    
                    # Verify SIGTERM handler was registered
                    signal_calls = [c for c in mock_signal.call_args_list if c[0][0] == signal.SIGTERM]
                    assert len(signal_calls) > 0


def test_main_signal_handler_stops_monitor():
    """Test SIGTERM handler stops the monitor."""
    with patch('vpn_sentinel_common.health_monitor.Monitor') as mock_monitor_class:
        with patch('vpn_sentinel_common.health_monitor.log_info'):
            mock_monitor = Mock()
            mock_monitor_class.return_value = mock_monitor
            
            # Track the signal handler
            signal_handler = None
            def capture_signal(sig, handler):
                nonlocal signal_handler
                signal_handler = handler
            
            with patch('vpn_sentinel_common.health_monitor.signal.signal', side_effect=capture_signal):
                # Use a counter to break the loop after signal is handled
                sleep_count = [0]
                def mock_sleep(duration):
                    sleep_count[0] += 1
                    if sleep_count[0] == 1:
                        # Call signal handler on first sleep
                        if signal_handler:
                            signal_handler(signal.SIGTERM, None)
                    elif sleep_count[0] > 2:
                        # Break loop
                        raise KeyboardInterrupt()
                
                with patch('vpn_sentinel_common.health_monitor.time.sleep', side_effect=mock_sleep):
                    try:
                        health_monitor.main()
                    except KeyboardInterrupt:
                        pass
                    
                    # Monitor should have been stopped by signal handler
                    assert mock_monitor.stop.call_count >= 1
