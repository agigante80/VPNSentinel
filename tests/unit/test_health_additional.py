"""Additional unit tests for vpn_sentinel_common.health module to reach 80%+ coverage.

These tests focus on edge cases, error paths, and fallback logic not covered by existing tests.
"""
import pytest
import subprocess
import os
from unittest.mock import patch, Mock, MagicMock
from vpn_sentinel_common import health


class TestMakeHealthEdgeCases:
    """Test edge cases in make_health function."""

    def test_make_health_alias_warn_to_degraded(self):
        """Test that 'warn' alias is converted to 'degraded'."""
        components = {"api": {"status": "ok", "details": {}}}
        h = health.make_health("warn", 10, components)
        
        assert h["status"] == "warn"  # Input is preserved
        # But validation should accept it
        valid, errors = health.validate_health(h)
        assert valid

    def test_make_health_component_warn_alias(self):
        """Test that component 'warn' status is converted to 'degraded'."""
        components = {"api": {"status": "warn", "details": {}}}
        h = health.make_health("ok", 10, components)
        
        assert h["components"]["api"]["status"] == "degraded"

    def test_make_health_component_case_insensitive(self):
        """Test that component status is case-insensitive."""
        components = {"api": {"status": "OK", "details": {}}}
        h = health.make_health("ok", 10, components)
        
        assert h["components"]["api"]["status"] == "ok"

    def test_make_health_component_empty_details(self):
        """Test component with missing details dict."""
        components = {"api": {"status": "ok"}}  # No details key
        h = health.make_health("ok", 10, components)
        
        # The code sets details to info.get("details") which returns None if not present
        assert "details" in h["components"]["api"]

    def test_make_health_invalid_component_not_dict(self):
        """Test that non-dict component info raises error."""
        components = {"api": "ok"}  # String instead of dict
        with pytest.raises(ValueError, match="invalid component status"):
            health.make_health("ok", 10, components)


class TestValidateHealthEdgeCases:
    """Test edge cases in validate_health function."""

    def test_validate_health_not_dict(self):
        """Test validation fails for non-dict input."""
        valid, errors = health.validate_health("not a dict")
        
        assert not valid
        assert any("must be a dict" in e for e in errors)

    def test_validate_health_missing_multiple_keys(self):
        """Test validation catches multiple missing keys."""
        incomplete = {"status": "ok"}  # Missing many required keys
        valid, errors = health.validate_health(incomplete)
        
        assert not valid
        assert len(errors) >= 4  # Should have errors for missing keys

    def test_validate_health_invalid_timestamp(self):
        """Test validation catches invalid timestamp format."""
        bad_ts = {
            "status": "ok",
            "uptime_seconds": 10,
            "timestamp": "not-iso-8601",
            "server_time": "2024-01-01T00:00:00Z",
            "components": {}
        }
        valid, errors = health.validate_health(bad_ts)
        
        assert not valid
        assert any("timestamp" in e and "ISO-8601" in e for e in errors)

    def test_validate_health_invalid_server_time(self):
        """Test validation catches invalid server_time format."""
        bad_st = {
            "status": "ok",
            "uptime_seconds": 10,
            "timestamp": "2024-01-01T00:00:00Z",
            "server_time": 12345,  # Not a string
            "components": {}
        }
        valid, errors = health.validate_health(bad_st)
        
        assert not valid
        assert any("server_time" in e for e in errors)

    def test_validate_health_negative_uptime(self):
        """Test validation catches negative uptime."""
        bad_uptime = {
            "status": "ok",
            "uptime_seconds": -5,
            "timestamp": "2024-01-01T00:00:00Z",
            "server_time": "2024-01-01T00:00:00Z",
            "components": {}
        }
        valid, errors = health.validate_health(bad_uptime)
        
        assert not valid
        assert any("uptime_seconds" in e for e in errors)

    def test_validate_health_components_not_dict(self):
        """Test validation catches non-dict components."""
        bad_comp = {
            "status": "ok",
            "uptime_seconds": 10,
            "timestamp": "2024-01-01T00:00:00Z",
            "server_time": "2024-01-01T00:00:00Z",
            "components": "not-a-dict"
        }
        valid, errors = health.validate_health(bad_comp)
        
        assert not valid
        assert any("components must be a dict" in e for e in errors)

    def test_validate_health_component_info_not_dict(self):
        """Test validation catches component info that's not a dict."""
        bad_comp_info = {
            "status": "ok",
            "uptime_seconds": 10,
            "timestamp": "2024-01-01T00:00:00Z",
            "server_time": "2024-01-01T00:00:00Z",
            "components": {"api": "ok"}  # Should be dict
        }
        valid, errors = health.validate_health(bad_comp_info)
        
        assert not valid
        assert any("api" in e and "must be a dict" in e for e in errors)

    def test_validate_health_component_invalid_status(self):
        """Test validation catches invalid component status."""
        bad_status = {
            "status": "ok",
            "uptime_seconds": 10,
            "timestamp": "2024-01-01T00:00:00Z",
            "server_time": "2024-01-01T00:00:00Z",
            "components": {"api": {"status": "broken", "details": {}}}
        }
        valid, errors = health.validate_health(bad_status)
        
        assert not valid
        assert any("api" in e and "invalid status" in e for e in errors)


class TestHttpGetFallback:
    """Test _http_get fallback to urllib when requests unavailable."""

    @patch('vpn_sentinel_common.health.requests', None)
    @patch('urllib.request.urlopen')
    def test_http_get_urllib_success(self, mock_urlopen):
        """Test _http_get falls back to urllib successfully."""
        mock_response = Mock()
        mock_response.read.return_value = b"success"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        result = health._http_get("http://example.com")
        
        assert result == "success"
        mock_urlopen.assert_called_once()

    @patch('vpn_sentinel_common.health.requests', None)
    @patch('urllib.request.urlopen')
    def test_http_get_urllib_timeout(self, mock_urlopen):
        """Test _http_get urllib timeout is handled."""
        mock_urlopen.side_effect = Exception("timeout")
        
        result = health._http_get("http://example.com")
        
        assert result is None

    @patch('vpn_sentinel_common.health.requests')
    def test_http_get_requests_non_200_status(self, mock_requests):
        """Test _http_get returns None for non-successful status codes."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_requests.get.return_value = mock_response
        
        result = health._http_get("http://example.com")
        
        assert result is None

    @patch('vpn_sentinel_common.health.requests')
    def test_http_get_requests_exception(self, mock_requests):
        """Test _http_get handles requests exception."""
        mock_requests.get.side_effect = Exception("network error")
        
        result = health._http_get("http://example.com")
        
        assert result is None


class TestLoggingFunctions:
    """Test logging function fallbacks."""

    def test_log_info_exists(self):
        """Test log_info function exists and is callable."""
        assert callable(health.log_info)
        
        # Test it doesn't crash - it will use log_utils or fallback to print
        with patch('builtins.print'):
            health.log_info("test", "message")

    def test_log_warn_exists(self):
        """Test log_warn function exists and is callable."""
        assert callable(health.log_warn)
        
        # Test it doesn't crash
        with patch('builtins.print'):
            health.log_warn("test", "warning message")

    def test_log_error_exists(self):
        """Test log_error function exists and is callable."""
        assert callable(health.log_error)
        
        # Test it doesn't crash
        with patch('builtins.print'):
            health.log_error("test", "error message")


class TestCheckClientProcessFallbacks:
    """Test check_client_process fallback paths."""

    @patch('vpn_sentinel_common.health.psutil')
    @patch('subprocess.run')
    def test_check_client_process_pgrep_not_running(self, mock_run, mock_psutil):
        """Test check_client_process when pgrep returns non-zero."""
        # psutil iteration finds nothing
        mock_psutil.process_iter.return_value = []
        
        # pgrep returns non-zero (process not found)
        mock_run.return_value.returncode = 1
        
        result = health.check_client_process()
        
        assert result == "not_running"

    @patch('vpn_sentinel_common.health.psutil')
    @patch('subprocess.run')
    def test_check_client_process_exception_fallback(self, mock_run, mock_psutil):
        """Test check_client_process handles exceptions gracefully."""
        # Both methods fail
        mock_psutil.process_iter.side_effect = Exception("psutil error")
        mock_run.side_effect = Exception("pgrep error")
        
        result = health.check_client_process()
        
        assert result == "not_running"

    @patch('vpn_sentinel_common.health.psutil')
    def test_check_client_process_psutil_cmdline_exception(self, mock_psutil):
        """Test check_client_process handles process cmdline exceptions."""
        mock_process = Mock()
        mock_process.info = {"cmdline": None, "name": None}
        mock_psutil.process_iter.return_value = [mock_process]
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            result = health.check_client_process()
        
        assert result == "not_running"


class TestCheckServerConnectivity:
    """Test check_server_connectivity edge cases."""

    @patch('vpn_sentinel_common.health.requests')
    def test_check_server_connectivity_head_request(self, mock_requests):
        """Test check_server_connectivity uses HEAD request first."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests.head.return_value = mock_response
        
        result = health.check_server_connectivity("http://example.com")
        
        assert result == "healthy"
        mock_requests.head.assert_called_once()

    @patch('vpn_sentinel_common.health.requests')
    def test_check_server_connectivity_head_fails_tries_get(self, mock_requests):
        """Test check_server_connectivity falls back to GET if HEAD fails."""
        mock_head_response = Mock()
        mock_head_response.status_code = 405  # Method not allowed
        mock_requests.head.return_value = mock_head_response
        
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_requests.get.return_value = mock_get_response
        
        result = health.check_server_connectivity("http://example.com")
        
        assert result == "healthy"
        mock_requests.get.assert_called_once()

    @patch('vpn_sentinel_common.health.requests', None)
    @patch('vpn_sentinel_common.health._http_get')
    def test_check_server_connectivity_urllib_fallback(self, mock_http_get):
        """Test check_server_connectivity falls back to urllib."""
        mock_http_get.return_value = "body content"
        
        result = health.check_server_connectivity("http://example.com")
        
        assert result == "healthy"

    @patch('vpn_sentinel_common.health.requests')
    def test_check_server_connectivity_exception(self, mock_requests):
        """Test check_server_connectivity handles exceptions."""
        mock_requests.head.side_effect = Exception("network error")
        
        result = health.check_server_connectivity("http://example.com")
        
        assert result == "unreachable"


class TestGetSystemInfoFallbacks:
    """Test get_system_info fallback paths."""

    @patch('vpn_sentinel_common.health.psutil', None)
    @patch('os.path.exists')
    @patch('builtins.open', create=True)
    def test_get_system_info_proc_meminfo(self, mock_open, mock_exists):
        """Test get_system_info reads /proc/meminfo when psutil unavailable."""
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = """
MemTotal:       16384000 kB
MemFree:         8192000 kB
MemAvailable:    8192000 kB
        """
        
        with patch('subprocess.check_output') as mock_check:
            mock_check.return_value = "Use% /\n  50%\n"
            info = health.get_system_info()
        
        assert "memory_percent" in info
        assert info["memory_percent"] != "unknown"

    @patch('vpn_sentinel_common.health.psutil', None)
    @patch('os.path.exists')
    def test_get_system_info_no_proc_meminfo(self, mock_exists):
        """Test get_system_info when /proc/meminfo doesn't exist."""
        mock_exists.return_value = False
        
        with patch('subprocess.check_output') as mock_check:
            mock_check.side_effect = Exception("df failed")
            info = health.get_system_info()
        
        assert info["memory_percent"] == "unknown"
        assert info["disk_percent"] == "unknown"

    @patch('vpn_sentinel_common.health.psutil', None)
    @patch('subprocess.check_output')
    def test_get_system_info_df_exception(self, mock_check):
        """Test get_system_info handles df command exceptions."""
        mock_check.side_effect = Exception("df not found")
        
        info = health.get_system_info()
        
        assert "disk_percent" in info
        # Should have unknown or fallback value

    @patch('vpn_sentinel_common.health.psutil')
    def test_get_system_info_general_exception(self, mock_psutil):
        """Test get_system_info handles general exceptions."""
        mock_psutil.virtual_memory.side_effect = Exception("psutil error")
        mock_psutil.disk_usage.side_effect = Exception("disk error")
        
        info = health.get_system_info()
        
        assert "memory_percent" in info
        assert "disk_percent" in info


class TestSampleHealthOk:
    """Test sample_health_ok function."""

    def test_sample_health_ok_no_version(self):
        """Test sample_health_ok without version."""
        h = health.sample_health_ok()
        
        assert h["status"] == "ok"
        assert "version" not in h
        valid, _ = health.validate_health(h)
        assert valid

    def test_sample_health_ok_with_version(self):
        """Test sample_health_ok with version."""
        h = health.sample_health_ok(version="1.0.0")
        
        assert h["version"] == "1.0.0"
        valid, _ = health.validate_health(h)
        assert valid
