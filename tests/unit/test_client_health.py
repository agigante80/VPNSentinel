"""
Unit tests for VPN Sentinel Client Health Check
Tests the health check script functionality
"""
import os
import sys
import unittest
import subprocess
import tempfile
import shutil


class TestClientHealthCheck(unittest.TestCase):
    """Test client health check script functionality"""

    def setUp(self):
        """Set up test environment"""
        # Get the path to the health check script
        self.script_dir = os.path.join(os.path.dirname(__file__), '../../vpn-sentinel-client')
        self.health_script = os.path.join(self.script_dir, 'healthcheck.sh')

        # Ensure the script exists
        if not os.path.exists(self.health_script):
            self.skipTest("Health check script not found")

    def test_health_script_exists_and_executable(self):
        """Test that the health check script exists and is executable"""
        self.assertTrue(os.path.exists(self.health_script))
        self.assertTrue(os.access(self.health_script, os.X_OK))

    def test_health_script_content(self):
        """Test that the health check script contains expected functionality"""
        with open(self.health_script, 'r') as f:
            content = f.read()

        # Should contain key health check logic - now sourced from common library
        self.assertIn('source "$LIB_DIR/health-common.sh"', content)
        self.assertIn('CLIENT_STATUS=$(check_client_process)', content)
        self.assertIn('NETWORK_STATUS=$(check_network_connectivity)', content)
        self.assertIn('SERVER_STATUS=$(check_server_connectivity)', content)
        self.assertIn('VPN_SENTINEL_URL', content)
        self.assertIn('✅ VPN Sentinel client is healthy', content)
        self.assertIn('❌ VPN Sentinel client script is not running', content)
        self.assertIn('❌ Cannot reach Cloudflare', content)

    def test_health_script_basic_execution(self):
        """Test that the health check script can be executed (basic smoke test)"""
        # Use a preserved copy of the current environment so installed tools
        # (python, pgrep, curl, etc.) remain discoverable in CI/container runs.
        env = os.environ.copy()

        # This should execute but may fail due to missing commands - that's OK for a smoke test
        try:
            result = subprocess.run([self.health_script], capture_output=True, text=True, env=env, timeout=5)
            # Script should have executed (even if it failed)
            self.assertIsInstance(result.returncode, int)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # If script can't execute at all, that's a problem
            self.fail("Health check script could not be executed")

    def test_health_script_with_helpful_error_messages(self):
        """Test that script provides helpful error messages"""
        with open(self.health_script, 'r') as f:
            content = f.read()

        # Should have clear error messages
        self.assertIn('VPN Sentinel client script is not running', content)
        self.assertIn('Cannot reach Cloudflare', content)
        self.assertIn('Cannot reach VPN Sentinel server', content)

        # Should have success message
        self.assertIn('VPN Sentinel client is healthy', content)

    def test_script_checks_process_status(self):
        """Test that script checks for running process"""
        with open(self.health_script, 'r') as f:
            content = f.read()

        # Should check if main script is running via common library function
        self.assertIn('check_client_process', content)
        self.assertIn('CLIENT_STATUS', content)

    def test_script_checks_external_connectivity(self):
        """Test that script checks external connectivity"""
        with open(self.health_script, 'r') as f:
            content = f.read()

        # Should check connectivity via common library function
        self.assertIn('check_network_connectivity', content)
        self.assertIn('NETWORK_STATUS', content)

    def test_script_handles_server_url_optional(self):
        """Test that script handles server URL as optional"""
        with open(self.health_script, 'r') as f:
            content = f.read()

        # Should check server connectivity via common library function
        self.assertIn('check_server_connectivity', content)
        self.assertIn('SERVER_STATUS', content)
        self.assertIn('VPN_SENTINEL_URL', content)

    def test_script_exit_codes(self):
        """Test that script uses appropriate exit codes"""
        with open(self.health_script, 'r') as f:
            content = f.read()

        # Should exit with 0 for success
        self.assertIn('exit 0', content)
        # Should exit with 1 for failure
        self.assertIn('exit 1', content)

    def test_script_uses_proper_curl_flags(self):
        """Test that script uses appropriate curl flags for health checks"""
        with open(self.health_script, 'r') as f:
            content = f.read()

        # Should use -f (fail on error), -s (silent), --max-time (timeout)
        self.assertIn('curl -f -s', content)
        self.assertIn('--max-time', content)

    def test_script_included_in_dockerfile(self):
        """Test that health check script is properly included in Dockerfile"""
        dockerfile_path = os.path.join(self.script_dir, 'Dockerfile')

        with open(dockerfile_path, 'r') as f:
            content = f.read()

        # Should copy the script
        self.assertIn('COPY vpn-sentinel-client/healthcheck.sh /app/healthcheck.sh', content)
        # Should make it executable (part of the chmod command)
        self.assertIn('/app/healthcheck.sh', content)
        self.assertIn('chmod +x', content)
        # Should use it in HEALTHCHECK
        self.assertIn('CMD /app/healthcheck.sh', content)

    def test_dockerfile_healthcheck_configuration(self):
        """Test that Dockerfile has proper HEALTHCHECK configuration"""
        dockerfile_path = os.path.join(self.script_dir, 'Dockerfile')

        with open(dockerfile_path, 'r') as f:
            content = f.read()

        # Should have HEALTHCHECK instruction
        self.assertIn('HEALTHCHECK', content)
        # Should have proper timing
        self.assertIn('--interval=', content)
        self.assertIn('--timeout=', content)
        self.assertIn('--start-period=', content)
        self.assertIn('--retries=', content)

    def test_enhanced_health_script_comprehensive_checks(self):
        """Test that the enhanced health check script performs all expected checks"""
        with open(self.health_script, 'r') as f:
            content = f.read()

        # Should contain enhanced health check logic
        self.assertIn('HEALTH_MONITOR_RUNNING', content)
        self.assertIn('VPN_SENTINEL_HEALTH_PORT', content)
        self.assertIn('memory_usage', content)
        self.assertIn('disk_usage', content)
        self.assertIn('--json', content)
        self.assertIn('high_memory_usage', content)
        self.assertIn('high_disk_usage', content)

    def test_enhanced_health_script_json_output(self):
        """Test that the enhanced health check script supports JSON output"""
        # Test with --json flag (would need mock environment)
        # This is a basic content check for now
        with open(self.health_script, 'r') as f:
            content = f.read()

        self.assertIn('"status":', content)
        self.assertIn('"checks":', content)
        self.assertIn('"warnings":', content)
        self.assertIn('client_process', content)
        self.assertIn('network_connectivity', content)
        self.assertIn('server_connectivity', content)
        self.assertIn('health_monitor', content)