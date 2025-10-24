"""
Unit tests for VPN Sentinel Health Common Library
Tests the shared health check functions used across components
"""
import os
import sys
import unittest
import subprocess
import tempfile
import shutil
import json


class TestHealthCommonLibrary(unittest.TestCase):
    """Test shared health common library functions"""

    def setUp(self):
        """Set up test environment"""
        # Get the path to the health common library
        self.lib_dir = os.path.join(os.path.dirname(__file__), '../../lib')
        self.health_common_script = os.path.join(self.lib_dir, 'health-common.sh')

        # Ensure the script exists
        if not os.path.exists(self.health_common_script):
            self.skipTest("Health common library not found")

    def test_health_common_library_exists(self):
        """Test that the health common library exists and is readable"""
        self.assertTrue(os.path.exists(self.health_common_script))
        self.assertTrue(os.access(self.health_common_script, os.R_OK))

    def test_health_common_library_content(self):
        """Test that the health common library contains expected functions"""
        with open(self.health_common_script, 'r') as f:
            content = f.read()

        # Should contain all expected functions
        self.assertIn('check_client_process()', content)
        self.assertIn('check_network_connectivity()', content)
        self.assertIn('check_server_connectivity()', content)
        self.assertIn('check_dns_leak_detection()', content)
        self.assertIn('get_system_info()', content)
        self.assertIn('log_message()', content)
        self.assertIn('log_info()', content)
        self.assertIn('log_error()', content)
        self.assertIn('log_warn()', content)

    def test_check_client_process_function(self):
        """Test that check_client_process function is properly defined"""
        with open(self.health_common_script, 'r') as f:
            content = f.read()

        # Should contain pgrep logic for client process
        self.assertIn('pgrep -f "vpn-sentinel-client.sh"', content)
        self.assertIn('echo "healthy"', content)
        self.assertIn('echo "not_running"', content)

    def test_check_network_connectivity_function(self):
        """Test that check_network_connectivity function is properly defined"""
        with open(self.health_common_script, 'r') as f:
            content = f.read()

        # Should contain curl logic for network connectivity
        self.assertIn('curl -f -s --max-time 5 "https://1.1.1.1/cdn-cgi/trace"', content)
        self.assertIn('echo "unreachable"', content)

    def test_check_server_connectivity_function(self):
        """Test that check_server_connectivity function is properly defined"""
        with open(self.health_common_script, 'r') as f:
            content = f.read()

        # Should contain server connectivity logic
        self.assertIn('VPN_SENTINEL_URL', content)
        self.assertIn('echo "not_configured"', content)
        self.assertIn('curl -s --max-time 10 -I', content)

    def test_check_dns_leak_detection_function(self):
        """Test that check_dns_leak_detection function is properly defined"""
        with open(self.health_common_script, 'r') as f:
            content = f.read()

        # Should contain DNS leak detection logic
        self.assertIn('curl -f -s --max-time 5 "https://ipinfo.io/json"', content)
        self.assertIn('echo "unavailable"', content)

    def test_get_system_info_function(self):
        """Test that get_system_info function is properly defined"""
        with open(self.health_common_script, 'r') as f:
            content = f.read()

        # Should contain system info collection logic
        self.assertIn('free | grep Mem', content)
        self.assertIn('df / | tail -1', content)
        self.assertIn('"memory_percent":', content)
        self.assertIn('"disk_percent":', content)

    def test_logging_functions(self):
        """Test that logging functions are properly defined"""
        with open(self.health_common_script, 'r') as f:
            content = f.read()

        # Should contain logging functions
        self.assertIn('date -u +"%Y-%m-%dT%H:%M:%SZ"', content)
        self.assertIn('log_message "INFO"', content)
        self.assertIn('log_message "ERROR"', content)
        self.assertIn('log_message "WARN"', content)

    def test_library_function_signatures(self):
        """Test that all functions have proper bash function signatures"""
        with open(self.health_common_script, 'r') as f:
            content = f.read()

        # All functions should be defined with proper bash syntax
        functions = [
            'log_message()',
            'log_info()',
            'log_error()',
            'log_warn()',
            'check_client_process()',
            'check_network_connectivity()',
            'check_server_connectivity()',
            'check_dns_leak_detection()',
            'get_system_info()'
        ]

        for func in functions:
            self.assertIn(func, content, f"Function {func} not found in library")

    def test_library_uses_relative_paths(self):
        """Test that library doesn't use absolute paths like /home/$USER"""
        with open(self.health_common_script, 'r') as f:
            content = f.read()

        # Should not contain absolute paths
        self.assertNotIn('/home/', content)
        self.assertNotIn('/usr/local/', content)
        # Should not contain hardcoded IP addresses for testing
        self.assertNotIn('192.168.', content)

    def test_library_error_handling(self):
        """Test that library functions include proper error handling"""
        with open(self.health_common_script, 'r') as f:
            content = f.read()

        # Should have error handling patterns
        self.assertIn('> /dev/null 2>&1', content)  # stderr redirection
        self.assertIn('return 0', content)  # success returns
        self.assertIn('return 1', content)  # failure returns

    def test_library_documentation(self):
        """Test that library has proper documentation"""
        with open(self.health_common_script, 'r') as f:
            content = f.read()

        # Should have header documentation
        self.assertIn('# VPN Sentinel Health Common Library', content)
        self.assertIn('# DESCRIPTION:', content)
        self.assertIn('# SHARED FUNCTIONS:', content)
        self.assertIn('# ENVIRONMENT VARIABLES:', content)
        self.assertIn('# USAGE:', content)
        self.assertIn('# Author: VPN Sentinel Project', content)
        self.assertIn('# License: MIT', content)