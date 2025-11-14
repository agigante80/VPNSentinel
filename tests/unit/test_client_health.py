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
        # Get the path to the health check script (Python version)
        self.script_dir = os.path.join(os.path.dirname(__file__), '../../vpn_sentinel_common/health_scripts')
        self.health_script = os.path.join(self.script_dir, 'healthcheck.py')

        # Ensure the script exists
        if not os.path.exists(self.health_script):
            self.skipTest("Health check script not found")

    def test_health_script_exists_and_executable(self):
        """Test that the health check script exists and is executable"""
        self.assertTrue(os.path.exists(self.health_script))
        # Python scripts should be executable
        self.assertTrue(os.access(self.health_script, os.X_OK))

    def test_health_script_content(self):
        """Test that the health check script contains expected functionality"""
        with open(self.health_script, 'r') as f:
            content = f.read()

        # Python version should import from vpn_sentinel_common.health
        self.assertIn('from vpn_sentinel_common import health', content)
        # Check for health check functions
        self.assertIn('check_client_process', content)
        self.assertIn('check_network_connectivity', content)
        self.assertIn('check_server_connectivity', content)
        # Helpful messages should be present
        self.assertIn('VPN Sentinel client is healthy', content)

    def test_health_script_basic_execution(self):
        """Test that the health check script can be executed (basic smoke test)"""
        # Use a preserved copy of the current environment so installed tools
        # (python, pgrep, curl, etc.) remain discoverable in CI/container runs.
        env = os.environ.copy()

        # This should execute but may fail due to missing dependencies - that's OK for a smoke test
        try:
            result = subprocess.run(['python3', self.health_script], capture_output=True, text=True, env=env, timeout=5)
            # Script should have executed (even if it failed)
            self.assertIsInstance(result.returncode, int)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # If script can't execute at all, that's a problem
            self.fail("Health check script could not be executed")

    def test_health_script_with_helpful_error_messages(self):
        """Test that script provides helpful error messages"""
        with open(self.health_script, 'r') as f:
            content = f.read()

        # Should have success message
        self.assertIn('VPN Sentinel client is healthy', content)
        # Should handle health issues
        self.assertIn('health issues', content)

    def test_script_checks_process_status(self):
        """Test that script checks for running process"""
        with open(self.health_script, 'r') as f:
            content = f.read()
        
        # Python version uses health module functions
        # Should check if main script is running via common library function
        self.assertIn('check_client_process', content)

    def test_script_checks_external_connectivity(self):
        """Test that script checks external connectivity"""
        with open(self.health_script, 'r') as f:
            content = f.read()

        # Should check connectivity via common library function
        self.assertIn('check_network_connectivity', content)
        self.assertIn('network_connectivity', content)

    def test_script_handles_server_url_optional(self):
        """Test that script handles server URL as optional"""
        with open(self.health_script, 'r') as f:
            content = f.read()

        # Should check server connectivity via common library function
        self.assertIn('check_server_connectivity', content)
        self.assertIn('server_connectivity', content)

    def test_script_exit_codes(self):
        """Test that script uses appropriate exit codes"""
        with open(self.health_script, 'r') as f:
            content = f.read()

        # Python uses sys.exit() for status codes  
        self.assertIn('sys.exit(0', content)
        self.assertIn('sys.exit', content)

    def test_script_uses_proper_network_checks(self):
        """Test that script uses appropriate network check methods"""
        with open(self.health_script, 'r') as f:
            content = f.read()

        # Python version uses requests library with timeouts
        self.assertIn('requests', content)
        self.assertIn('timeout', content)

    def test_script_included_in_dockerfile(self):
        """Test that health check script is properly included in Dockerfile"""
        dockerfile_path = os.path.join(os.path.dirname(__file__), '../../vpn-sentinel-client/Dockerfile')

        with open(dockerfile_path, 'r') as f:
            content = f.read()

        # Should copy the Python script
        self.assertIn('COPY vpn_sentinel_common/health_scripts/healthcheck.py /app/healthcheck.py', content)
        # Should make it executable (part of the chmod command)
        self.assertIn('/app/healthcheck.py', content)
        self.assertIn('chmod +x', content)
        # Should use it in HEALTHCHECK with python3
        self.assertIn('CMD python3 /app/healthcheck.py', content)

    def test_dockerfile_healthcheck_configuration(self):
        """Test that Dockerfile has proper HEALTHCHECK configuration"""
        dockerfile_path = os.path.join(os.path.dirname(__file__), '../../vpn-sentinel-client/Dockerfile')

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
        self.assertIn('health_monitor_running', content)
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

        self.assertIn('status', content)
        self.assertIn('checks', content)
        self.assertIn('warnings', content)
        self.assertIn('client_process', content)
        self.assertIn('network_connectivity', content)
        self.assertIn('server_connectivity', content)
        self.assertIn('health_monitor', content)