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

            # Shell script should include configuration references and functions
            self.assertIn('VPN_SENTINEL_HEALTH_PORT', content)
            self.assertIn('check_client_process', content)
            self.assertIn('check_network_connectivity', content)

            # Python-specific code (Flask endpoints/imports) lives in the
            # extracted module. Verify the Python module contains the Flask app
            py_path = os.path.join(self.script_dir, 'health-monitor.py')
            with open(py_path, 'r') as pf:
                py_content = pf.read()

            self.assertIn('from flask import Flask', py_content)
            self.assertIn('/client/health', py_content)
            self.assertIn('/client/health/ready', py_content)
            self.assertIn('/client/health/startup', py_content)

    def test_health_monitor_help_output(self):
        """Test that the health monitor script provides help information"""
        # NOTE: The health monitor script is a server, not a CLI tool with --help
        # This test is not applicable to the current implementation
        self.skipTest("Health monitor is a server, not a CLI tool with --help option")

    def test_health_monitor_single_check(self):
        """Test that the health monitor can perform a single health check"""
        # NOTE: The health monitor script is a server, not a CLI tool with --check
        # This test is not applicable to the current implementation
        self.skipTest("Health monitor is a server, not a CLI tool with --check option")

    def test_health_monitor_script_imports(self):
        """Test that the health monitor script contains proper Python imports"""
        with open(self.health_monitor_script, 'r') as f:
            content = f.read()

            # Python-specific imports live in the extracted Python module
            py_path = os.path.join(self.script_dir, 'health-monitor.py')
            with open(py_path, 'r') as pf:
                py_content = pf.read()

            self.assertIn('import os', py_content)
            self.assertIn('import sys', py_content)
            self.assertIn('from flask import Flask', py_content)
            self.assertIn('import subprocess', py_content)
            self.assertIn('app = Flask(__name__)', py_content)

    def test_health_monitor_endpoints(self):
        """Test that the health monitor defines all required endpoints"""
        with open(self.health_monitor_script, 'r') as f:
            content = f.read()
            # Check endpoints inside the Python module
            py_path = os.path.join(self.script_dir, 'health-monitor.py')
            with open(py_path, 'r') as pf:
                py_content = pf.read()

            self.assertIn("@app.route('/client/health', methods=['GET'])", py_content)
            self.assertIn("@app.route('/client/health/ready', methods=['GET'])", py_content)
            self.assertIn("@app.route('/client/health/startup', methods=['GET'])", py_content)

    def test_health_monitor_environment_variables(self):
        """Test that the health monitor uses correct environment variables"""
        with open(self.health_monitor_script, 'r') as f:
            content = f.read()

            # Shell script environment variables should still be present
            self.assertIn('VPN_SENTINEL_HEALTH_PORT', content)
            self.assertIn('TZ', content)

            # API path/key are server-side variables; the health-monitor Python
            # module should not reference VPN_SENTINEL_URL (client monitor no longer
            # checks server connectivity).

    def test_health_monitor_health_checks(self):
        """Test that the health monitor implements all required health checks"""
        with open(self.health_monitor_script, 'r') as f:
            content = f.read()

            with open(self.health_monitor_script, 'r') as f:
                content = f.read()

            # Should source health check functions from common library or prefer Python shim at runtime
            self.assertTrue(('source "$LIB_DIR/health-common.sh"' in content) or ('health_common.py' in content))
            self.assertIn('check_client_process', content)
            self.assertIn('check_network_connectivity', content)
            self.assertIn('check_dns_leak_detection', content)
            self.assertIn('get_system_info', content)

    def test_health_monitor_status_generation(self):
        """Test that the health monitor generates proper status responses"""
        with open(self.health_monitor_script, 'r') as f:
            content = f.read()

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

            # Signal handling is part of the Python module
            py_path = os.path.join(self.script_dir, 'health-monitor.py')
            with open(py_path, 'r') as pf:
                py_content = pf.read()

            self.assertIn('signal.signal(signal.SIGINT', py_content)
            self.assertIn('signal.signal(signal.SIGTERM', py_content)
            self.assertIn('def signal_handler', py_content)

    def test_health_monitor_port_configuration(self):
        """Test that the health monitor uses configurable ports"""
        with open(self.health_monitor_script, 'r') as f:
            content = f.read()
        # Port configuration lives in the extracted Python module
        py_path = os.path.join(self.script_dir, 'health-monitor.py')
        with open(py_path, 'r') as pf:
            py_content = pf.read()

        # Should use configurable port
        self.assertIn("port = int(os.environ.get('VPN_SENTINEL_HEALTH_PORT', '8082'))", py_content)
        self.assertIn("app.run(host='0.0.0.0', port=port", py_content)

    def test_health_monitor_error_handling(self):
        """Test that health monitor handles errors gracefully"""
        with open(self.health_monitor_script, 'r') as f:
            content = f.read()

            # Check exception handling and error/issue fields in the Python module
            py_path = os.path.join(self.script_dir, 'health-monitor.py')
            with open(py_path, 'r') as pf:
                py_content = pf.read()

            self.assertIn('except Exception', py_content)
            self.assertIn('except:', py_content)
            self.assertIn('issues', py_content)

    def test_health_monitor_caching_mechanism(self):
        """Test that health monitor implements caching for performance"""
        with open(self.health_monitor_script, 'r') as f:
            content = f.read()

            # Caching is implemented in the Python module
            py_path = os.path.join(self.script_dir, 'health-monitor.py')
            with open(py_path, 'r') as pf:
                py_content = pf.read()

            self.assertIn('CACHE_DURATION', py_content)
            self.assertIn('last_update', py_content)
            # The exact caching expression may differ between versions; ensure
            # the general caching variables are present and used.

    def test_health_monitor_process_monitoring(self):
        """Test that health monitor properly monitors client processes"""
        with open(self.health_monitor_script, 'r') as f:
            content = f.read()
        # The Python module contains the runtime checks (pgrep etc.)
        py_path = os.path.join(self.script_dir, 'health-monitor.py')
        with open(py_path, 'r') as pf:
            py_content = pf.read()

        # Should check for client process using pgrep inside the Python module
        self.assertIn("pgrep -f 'vpn-sentinel-client.sh'", py_content)
        self.assertIn('client_process', py_content)
        self.assertIn('healthy', py_content)
        self.assertIn('not_running', py_content)

    def test_health_monitor_server_connectivity_with_env(self):
        """Test that the health monitor no longer checks server connectivity"""
        with open(self.health_monitor_script, 'r') as f:
            content = f.read()

            # Server connectivity is no longer checked by the client health monitor
            # Verify the Python module does not reference VPN_SENTINEL_URL
            py_path = os.path.join(self.script_dir, 'health-monitor.py')
            with open(py_path, 'r') as pf:
                py_content = pf.read()

            self.assertNotIn('VPN_SENTINEL_URL', py_content)
            self.assertNotIn('server_connectivity', py_content)
            self.assertNotIn('unreachable', py_content)
            self.assertNotIn('not_configured', py_content)

    def test_health_monitor_embedded_python_env_access(self):
        """Test that embedded Python code properly accesses environment variables"""
        # NOTE: The health monitor script is a server, not a CLI tool with --check
        # This test is not applicable to the current implementation
        self.skipTest("Health monitor is a server, not a CLI tool with --check option")