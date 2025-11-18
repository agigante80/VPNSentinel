"""Unit tests for file logging in log_utils."""
import os
import tempfile
import pytest
from vpn_sentinel_common.log_utils import log_info, log_error, log_warn


class TestFileLogging:
    """Test file logging functionality."""
    
    def test_log_to_file_when_env_var_set(self, monkeypatch, tmp_path):
        """Test that logs are written to file when VPN_SENTINEL_LOG_FILE is set."""
        log_file = tmp_path / "test.log"
        monkeypatch.setenv('VPN_SENTINEL_LOG_FILE', str(log_file))
        
        # Need to reload module to pick up new env var
        import importlib
        import vpn_sentinel_common.log_utils
        importlib.reload(vpn_sentinel_common.log_utils)
        from vpn_sentinel_common.log_utils import log_info
        
        # Log some messages
        log_info("test", "Test message 1")
        log_info("test", "Test message 2")
        
        # Verify file was created and contains logs
        assert log_file.exists()
        content = log_file.read_text()
        assert "INFO [test] Test message 1" in content
        assert "INFO [test] Test message 2" in content
    
    def test_log_to_stdout_only_when_no_env_var(self, monkeypatch, capsys):
        """Test that logs go to stdout when no file is configured."""
        monkeypatch.delenv('VPN_SENTINEL_LOG_FILE', raising=False)
        
        # Reload module
        import importlib
        import vpn_sentinel_common.log_utils
        importlib.reload(vpn_sentinel_common.log_utils)
        from vpn_sentinel_common.log_utils import log_info
        
        log_info("test", "Test stdout message")
        
        captured = capsys.readouterr()
        assert "INFO [test] Test stdout message" in captured.out
    
    def test_log_creates_directory_if_missing(self, monkeypatch, tmp_path):
        """Test that log file directory is created if it doesn't exist."""
        log_dir = tmp_path / "subdir" / "logs"
        log_file = log_dir / "server.log"
        monkeypatch.setenv('VPN_SENTINEL_LOG_FILE', str(log_file))
        
        # Reload module
        import importlib
        import vpn_sentinel_common.log_utils
        importlib.reload(vpn_sentinel_common.log_utils)
        from vpn_sentinel_common.log_utils import log_info
        
        log_info("test", "Test message")
        
        # Verify directory and file were created
        assert log_dir.exists()
        assert log_file.exists()
        assert "INFO [test] Test message" in log_file.read_text()
    
    def test_continues_on_file_write_error(self, monkeypatch, tmp_path, capsys):
        """Test that logging continues even if file write fails."""
        # Create a read-only file
        log_file = tmp_path / "readonly.log"
        log_file.touch()
        os.chmod(log_file, 0o444)  # Read-only
        
        monkeypatch.setenv('VPN_SENTINEL_LOG_FILE', str(log_file))
        
        # Reload module - this should handle the error gracefully
        import importlib
        import vpn_sentinel_common.log_utils
        importlib.reload(vpn_sentinel_common.log_utils)
        from vpn_sentinel_common.log_utils import log_info
        
        # Should not raise exception, still logs to stdout
        log_info("test", "Test message after error")
        
        captured = capsys.readouterr()
        assert "INFO [test] Test message after error" in captured.out
