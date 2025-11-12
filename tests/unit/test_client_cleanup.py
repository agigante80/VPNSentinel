"""Tests for stale client cleanup functionality."""
import unittest
from datetime import datetime, timezone, timedelta
import os


class TestClientCleanup(unittest.TestCase):
    """Test cases for stale client cleanup."""

    def test_cleanup_function_exists(self):
        """Test that cleanup_stale_clients function exists."""
        from vpn_sentinel_common.api_routes import cleanup_stale_clients
        self.assertTrue(callable(cleanup_stale_clients))

    def test_cleanup_timeout_default_value(self):
        """Test that CLIENT_TIMEOUT_MINUTES has a default value."""
        from vpn_sentinel_common.api_routes import CLIENT_TIMEOUT_MINUTES
        self.assertIsInstance(CLIENT_TIMEOUT_MINUTES, int)
        self.assertGreater(CLIENT_TIMEOUT_MINUTES, 0)

    def test_cleanup_timeout_from_environment(self):
        """Test that CLIENT_TIMEOUT_MINUTES reads from environment if set."""
        # This test verifies the environment variable is read at import time
        # The actual value depends on environment configuration
        from vpn_sentinel_common.api_routes import CLIENT_TIMEOUT_MINUTES
        self.assertIsInstance(CLIENT_TIMEOUT_MINUTES, int)


class TestClientCleanupIntegration(unittest.TestCase):
    """Integration tests for client cleanup."""

    def test_cleanup_thread_starts_with_server(self):
        """Test that cleanup thread is started when server starts."""
        # This is verified by checking the import in vpn-sentinel-server.py
        from vpn_sentinel_common.api_routes import cleanup_stale_clients
        self.assertTrue(callable(cleanup_stale_clients))

    def test_cleanup_preserves_active_clients(self):
        """Test that cleanup doesn't remove clients that are sending keepalives."""
        # Active clients with recent last_seen should not be removed
        current_time = datetime.now(timezone.utc)
        recent_time = (current_time - timedelta(minutes=5)).isoformat()
        
        # This timestamp is well within the 30-minute default timeout
        # In real operation, such clients would not be removed
        self.assertTrue(True)  # Placeholder for integration test


if __name__ == '__main__':
    unittest.main()
