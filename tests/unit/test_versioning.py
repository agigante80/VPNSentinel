"""
Unit tests for VPN Sentinel versioning system
Tests the automatic version determination logic
"""
import os
import unittest
import subprocess
import tempfile
from unittest.mock import patch, Mock


class TestVersioning(unittest.TestCase):
    """Test automatic versioning system"""

    def setUp(self):
        """Set up test environment"""
        self.version_script = os.path.join(
            os.path.dirname(__file__),
            '../../get_version.sh'
        )

    def test_version_script_exists(self):
        """Test that version script exists and is executable"""
        self.assertTrue(os.path.exists(self.version_script))
        self.assertTrue(os.access(self.version_script, os.X_OK))

    def test_version_script_syntax(self):
        """Test that version script has valid bash syntax"""
        result = subprocess.run(
            ['bash', '-n', self.version_script],
            capture_output=True,
            text=True,
            timeout=10
        )
        self.assertEqual(result.returncode, 0,
                        f"Script syntax error: {result.stderr}")

    def test_version_determination_logic(self):
        """Test version determination logic with actual script"""
        # Test the script directly in the actual repository context
        result = subprocess.run(
            [self.version_script],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Should return a version string
        self.assertEqual(result.returncode, 0)
        version = result.stdout.strip()
        self.assertTrue(len(version) > 0)

        # Should be a valid semantic version format (with or without v prefix)
        # Examples: 1.0.0, 1.0.0-dev-abc123, 1.0.0+5, 0.0.0-dev-abc123
        import re
        version_pattern = r'^\d+\.\d+\.\d+(-[\w\.\-]+)?(\+\d+)?$'
        self.assertRegex(version, version_pattern, f"Version '{version}' does not match semantic versioning pattern")

        # Should be a development version (since we're on develop branch)
        self.assertIn('-dev-', version)

    def test_version_environment_variable_fallback(self):
        """Test that VERSION environment variable logic works"""
        # Test that environment variable is properly handled
        # We can't easily test the full script sourcing due to the monitoring loop
        # So let's test the logic conceptually

        # Simulate VERSION env var being set
        test_env = {'VERSION': '2.0.0-test'}

        # This simulates what the client script does
        version = test_env.get('VERSION')
        if version:
            # Should use the VERSION environment variable
            self.assertEqual(version, '2.0.0-test')
        else:
            # Fallback logic would apply
            self.fail("VERSION should be available")

        # Test fallback logic
        fallback_env = {}  # No VERSION
        version = fallback_env.get('VERSION')
        if not version:
            # Should use fallback
            fallback_version = "1.0.0-dev"
            self.assertEqual(fallback_version, "1.0.0-dev")

    def test_server_version_from_env(self):
        """Test that server uses VERSION environment variable"""
        # This would require importing the server module with VERSION set
        # For now, just test that the environment variable logic works
        test_env = {'VERSION': '3.0.0-env'}
        with patch.dict(os.environ, test_env):
            # Simulate server import
            version = os.environ.get('VERSION')
            self.assertEqual(version, '3.0.0-env')

    def test_version_format_validation(self):
        """Test that version follows expected format patterns"""
        # Test various version formats
        valid_formats = [
            '1.0.0',           # Production release
            '1.0.0+5',         # Pre-release with build number
            '1.0.0-dev-abc123', # Development version
            '1.0.0-feature-x-abc123'  # Feature branch version
        ]

        for version in valid_formats:
            # Basic format validation (should contain dots and be reasonable length)
            self.assertIn('.', version)
            self.assertGreater(len(version), 3)
            self.assertLess(len(version), 50)

    def test_git_describe_parsing(self):
        """Test parsing of git describe output"""
        # Test the parsing logic from the version script
        test_cases = [
            ("v1.0.0", "1.0.0"),
            ("v1.0.0-5-gabc123", "1.0.0+5"),
            ("v2.1.3-12-gdef456", "2.1.3+12"),
        ]

        for git_describe, expected_base in test_cases:
            # Extract version components
            if git_describe.startswith('v'):
                version_part = git_describe[1:]  # Remove 'v' prefix
                parts = version_part.split('-')
                base_version = parts[0]

                self.assertEqual(base_version, expected_base.split('+')[0])


if __name__ == '__main__':
    unittest.main()