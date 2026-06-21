"""Tests for client process detection health check."""

import unittest
from unittest.mock import patch, Mock
from vpn_sentinel.common.health import check_client_process


class TestClientProcessDetection(unittest.TestCase):
    """Test client process detection for both Python and shell scripts."""

    @patch("vpn_sentinel.common.health.subprocess.run")
    @patch("vpn_sentinel.common.health.psutil", None)
    def test_detects_python_client(self, mock_run):
        """Test that Python client (python -m vpn_sentinel.client) is detected."""
        # Mock pgrep finding the Python client
        mock_run.return_value = Mock(returncode=0)

        result = check_client_process()

        assert result == "healthy"
        # Should try multiple patterns
        assert mock_run.call_count >= 1

    @patch("vpn_sentinel.common.health.subprocess.run")
    @patch("vpn_sentinel.common.health.psutil", None)
    def test_detects_shell_client(self, mock_run):
        """Test that shell client (vpn-sentinel-client.sh) is detected."""
        # First call fails (Python), second succeeds (shell)
        mock_run.side_effect = [
            Mock(returncode=1),  # Python not found
            Mock(returncode=0),  # Shell found
        ]

        result = check_client_process()

        assert result == "healthy"

    @patch("vpn_sentinel.common.health.subprocess.run")
    @patch("vpn_sentinel.common.health.psutil", None)
    def test_not_running_when_no_process(self, mock_run):
        """Test that 'not_running' returned when no client process found."""
        # All patterns fail
        mock_run.return_value = Mock(returncode=1)

        result = check_client_process()

        assert result == "not_running"

    @patch("vpn_sentinel.common.health.psutil")
    def test_uses_psutil_when_available(self, mock_psutil):
        """Test that psutil is used when available."""
        # Mock process with Python client (python -m vpn_sentinel.client) in cmdline
        mock_proc = Mock()
        mock_proc.info = {"cmdline": ["/usr/bin/python3", "-m", "vpn_sentinel.client"], "name": "python3"}
        mock_psutil.process_iter.return_value = [mock_proc]

        result = check_client_process()

        assert result == "healthy"
        mock_psutil.process_iter.assert_called_once()

    @patch("vpn_sentinel.common.health.psutil")
    def test_psutil_detects_shell_client(self, mock_psutil):
        """Test that psutil detects shell client."""
        # Mock process with shell client in cmdline
        mock_proc = Mock()
        mock_proc.info = {"cmdline": ["/bin/sh", "/app/vpn-sentinel-client.sh"], "name": "sh"}
        mock_psutil.process_iter.return_value = [mock_proc]

        result = check_client_process()

        assert result == "healthy"

    @patch("vpn_sentinel.common.health.subprocess.run")
    @patch("vpn_sentinel.common.health.psutil", None)
    def test_custom_process_name(self, mock_run):
        """Test that custom process name is also checked."""
        # First call succeeds on first pattern
        mock_run.return_value = Mock(returncode=0)

        result = check_client_process("my-custom-client")

        assert result == "healthy"
        # Verify pgrep was called (at least once)
        assert mock_run.call_count >= 1


if __name__ == "__main__":
    unittest.main()
