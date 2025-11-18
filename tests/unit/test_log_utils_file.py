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
    
    def test_log_to_default_file_when_no_env_var(self, monkeypatch, tmp_path, capsys):
        """Test that logs go to default /tmp location when no env var is set."""
        # Set up a temp directory to simulate /tmp
        default_log = tmp_path / "vpn-sentinel-server.log"
        monkeypatch.setenv('VPN_SENTINEL_LOG_FILE', str(default_log))
        
        # Reload module
        import importlib
        import vpn_sentinel_common.log_utils
        importlib.reload(vpn_sentinel_common.log_utils)
        from vpn_sentinel_common.log_utils import log_info
        
        log_info("test", "Test default file message")
        
        # Should write to both stdout and file
        captured = capsys.readouterr()
        assert "INFO [test] Test default file message" in captured.out
        assert default_log.exists()
        assert "INFO [test] Test default file message" in default_log.read_text()
    
    def test_log_disabled_with_empty_string(self, monkeypatch, capsys):
        """Test that file logging can be explicitly disabled with empty string."""
        monkeypatch.setenv('VPN_SENTINEL_LOG_FILE', '')
        
        # Reload module
        import importlib
        import vpn_sentinel_common.log_utils
        importlib.reload(vpn_sentinel_common.log_utils)
        from vpn_sentinel_common.log_utils import log_info
        
        log_info("test", "Test stdout only message")
        
        # Should only log to stdout
        captured = capsys.readouterr()
        assert "INFO [test] Test stdout only message" in captured.out
    
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
    
    def test_log_rotation_creates_backup_files(self, monkeypatch, tmp_path):
        """Test that log rotation creates backup files when size limit is reached."""
        log_file = tmp_path / "test.log"
        
        # Set small max size to trigger rotation easily (1KB)
        monkeypatch.setenv('VPN_SENTINEL_LOG_FILE', str(log_file))
        monkeypatch.setenv('VPN_SENTINEL_LOG_MAX_SIZE', '1024')
        monkeypatch.setenv('VPN_SENTINEL_LOG_MAX_BACKUPS', '3')
        
        # Reload module to pick up new env vars
        import importlib
        import vpn_sentinel_common.log_utils
        importlib.reload(vpn_sentinel_common.log_utils)
        from vpn_sentinel_common.log_utils import log_info
        
        # Write enough logs to trigger rotation
        for i in range(50):
            log_info("test", f"Test message {i} with padding to increase size " + "x" * 50)
        
        # Should have created main log + backup files
        assert log_file.exists()
        assert (tmp_path / "test.log.1").exists()
        assert (tmp_path / "test.log.2").exists()
        assert (tmp_path / "test.log.3").exists()
        
        # Should not create more than MAX_BACKUPS
        assert not (tmp_path / "test.log.4").exists()
        
        # Each file should be under the size limit (with some tolerance for last write)
        for backup_num in [1, 2, 3]:
            backup_file = tmp_path / f"test.log.{backup_num}"
            assert backup_file.stat().st_size <= 1024 * 1.2  # 20% tolerance
    
    def test_log_rotation_config_defaults(self, monkeypatch, tmp_path):
        """Test that log rotation uses sensible defaults."""
        log_file = tmp_path / "test.log"
        monkeypatch.setenv('VPN_SENTINEL_LOG_FILE', str(log_file))
        
        # Don't set size/backup env vars, should use defaults
        monkeypatch.delenv('VPN_SENTINEL_LOG_MAX_SIZE', raising=False)
        monkeypatch.delenv('VPN_SENTINEL_LOG_MAX_BACKUPS', raising=False)
        
        # Reload module
        import importlib
        import vpn_sentinel_common.log_utils
        importlib.reload(vpn_sentinel_common.log_utils)
        from vpn_sentinel_common.log_utils import log_info
        
        log_info("test", "Test with default rotation config")
        
        # Should create log file with default settings (10MB max, 5 backups)
        assert log_file.exists()
        
        # Check defaults are loaded correctly
        from vpn_sentinel_common import log_utils
        assert log_utils.MAX_LOG_SIZE_BYTES == 10 * 1024 * 1024  # 10 MB
        assert log_utils.MAX_LOG_BACKUPS == 5
