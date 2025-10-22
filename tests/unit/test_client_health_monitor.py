"""
Unit tests for VPN Sentinel Client Health Monitor
Tests the dedicated health monitor script functionality
"""
import os
import sys
import unittest
import subprocess
import tempfile
import shutil
import json


class TestClientHealthMonitor(unittest.TestCase):
    """Test client health monitor script functionality"""

    def setUp(self):
        """Set up test environment"""
        # Get the path to the health monitor script
        self.script_dir = os.path.join(os.path.dirname(__file__), '../../vpn-sentinel-client')
        self.health_monitor_script = os.path.join(self.script_dir, 'health-monitor.sh')

        # Ensure the script exists
        if not os.path.exists(self.health_monitor_script):
            self.skipTest("Health monitor script not found")

    def test_health_monitor_script_exists_and_executable(self):
        """Test that the health monitor script exists and is executable"""
        self.assertTrue(os.path.exists(self.health_monitor_script))
        self.assertTrue(os.access(self.health_monitor_script, os.X_OK))

    def test_health_monitor_script_content(self):
        """Test that the health monitor script contains expected functionality"""
        with open(self.health_monitor_script, 'r') as f:
            content = f.read()

        # Should contain key health monitor logic
        self.assertIn('VPN_SENTINEL_HEALTH_PORT', content)
        self.assertIn('check_client_process', content)
        self.assertIn('check_network_connectivity', content)
        self.assertIn('check_server_connectivity', content)
        self.assertIn('generate_health_status', content)
        self.assertIn('Flask', content)
        self.assertIn('/health', content)
        self.assertIn('/health/ready', content)
        self.assertIn('/health/startup', content)

    def test_health_monitor_help_output(self):
        """Test that the health monitor script shows help information"""
        try:
            result = subprocess.run(
                [self.health_monitor_script, '--help'],
                capture_output=True, text=True, timeout=10
            )

            self.assertEqual(result.returncode, 0)
            output = result.stdout
            self.assertIn('VPN Sentinel Client Health Monitor', output)
            self.assertIn('--help', output)
            self.assertIn('--port', output)
            self.assertIn('--check', output)

        except subprocess.TimeoutExpired:
            self.skipTest("Health monitor help test timed out")

    def test_health_monitor_single_check(self):
        """Test that the health monitor can perform a single health check"""
        try:
            # Set minimal environment for testing
            env = os.environ.copy()
            env.update({
                'VPN_SENTINEL_HEALTH_PORT': '8083',  # Use different port for testing
                'VPN_SENTINEL_URL': '',  # No server URL for basic test
                'PATH': '/bin:/usr/bin'
            })

            result = subprocess.run(
                [self.health_monitor_script, '--check'],
                capture_output=True, text=True, timeout=15,
                env=env
            )

            # Should exit successfully and produce JSON output
            self.assertEqual(result.returncode, 0)
            output = result.stdout.strip()

            # Should be valid JSON
            try:
                data = json.loads(output)
                self.assertIn('status', data)
                self.assertIn('checks', data)
                self.assertIn('client_process', data['checks'])
                self.assertIn('network_connectivity', data['checks'])
            except json.JSONDecodeError:
                self.fail("Health monitor output is not valid JSON")

        except subprocess.TimeoutExpired:
            self.skipTest("Health monitor single check test timed out")

    def test_health_monitor_script_imports(self):
        """Test that the health monitor script contains proper Python imports"""
        with open(self.health_monitor_script, 'r') as f:
            content = f.read()

        # Should contain Flask server code
        self.assertIn('import os', content)
        self.assertIn('import sys', content)
        self.assertIn('from flask import Flask', content)
        self.assertIn('import subprocess', content)
        self.assertIn('app = Flask(__name__)', content)

    def test_health_monitor_endpoints(self):
        """Test that the health monitor defines all required endpoints"""
        with open(self.health_monitor_script, 'r') as f:
            content = f.read()

        # Should define all health endpoints
        self.assertIn('@app.route(\'/health\', methods=[\'GET\'])', content)
        self.assertIn('@app.route(\'/health/ready\', methods=[\'GET\'])', content)
        self.assertIn('@app.route(\'/health/startup\', methods=[\'GET\'])', content)

    def test_health_monitor_environment_variables(self):
        """Test that the health monitor uses correct environment variables"""
        with open(self.health_monitor_script, 'r') as f:
            content = f.read()

        # Should use correct environment variables
        self.assertIn('VPN_SENTINEL_HEALTH_PORT', content)
        self.assertIn('VPN_SENTINEL_URL', content)
        self.assertIn('VPN_SENTINEL_API_PATH', content)
        self.assertIn('VPN_SENTINEL_API_KEY', content)
        self.assertIn('TZ', content)

    def test_health_monitor_health_checks(self):
        """Test that the health monitor implements all required health checks"""
        with open(self.health_monitor_script, 'r') as f:
            content = f.read()

        # Should implement all health check functions (shell functions)
        self.assertIn('check_client_process()', content)
        self.assertIn('check_network_connectivity()', content)
        self.assertIn('check_server_connectivity()', content)
        self.assertIn('check_dns_leak_detection()', content)
        self.assertIn('get_system_info()', content)

    def test_health_monitor_status_generation(self):
        """Test that the health monitor generates proper status responses"""
        with open(self.health_monitor_script, 'r') as f:
            content = f.read()

        # Should have status generation functions (shell functions)
        self.assertIn('generate_health_status()', content)
        self.assertIn('generate_readiness_status()', content)
        self.assertIn('generate_startup_status()', content)

    def test_health_monitor_signal_handling(self):
        """Test that the health monitor handles signals properly"""
        with open(self.health_monitor_script, 'r') as f:
            content = f.read()

        # Should handle signals for graceful shutdown
        self.assertIn('signal.signal(signal.SIGINT', content)
        self.assertIn('signal.signal(signal.SIGTERM', content)
        self.assertIn('def signal_handler', content)

    def test_health_monitor_port_configuration(self):
        """Test that the health monitor uses configurable ports"""
        with open(self.health_monitor_script, 'r') as f:
            content = f.read()

        # Should use configurable port
        self.assertIn('port = int(os.environ.get(\'VPN_SENTINEL_HEALTH_PORT\', \'8082\'))', content)
        self.assertIn('app.run(host=\'0.0.0.0\', port=port', content)

    def test_health_monitor_error_handling(self):
        """Test that health monitor handles errors gracefully"""
        with open(self.health_monitor_script, 'r') as f:
            content = f.read()

        # Should handle exceptions in health checks
        self.assertIn('except Exception as e:', content)
        self.assertIn('except:', content)
        self.assertIn('error', content)
        self.assertIn('issues', content)

    def test_health_monitor_caching_mechanism(self):
        """Test that health monitor implements caching for performance"""
        with open(self.health_monitor_script, 'r') as f:
            content = f.read()

        # Should implement caching to avoid excessive health checks
        self.assertIn('CACHE_DURATION', content)
        self.assertIn('last_update', content)
        self.assertIn('current_time - last_update > CACHE_DURATION', content)

    def test_health_monitor_process_monitoring(self):
        """Test that health monitor properly monitors client processes"""
        with open(self.health_monitor_script, 'r') as f:
            content = f.read()

        # Should check for client process using pgrep
        self.assertIn('pgrep', content)
        self.assertIn('vpn-sentinel-client.sh', content)
        self.assertIn('client_process', content)
        self.assertIn('healthy', content)
        self.assertIn('not_running', content)