"""Unit tests for vpn_sentinel_common.version module.

Tests version management functions including environment variable handling,
git commit hash retrieval, and version info generation.
"""
import pytest
import subprocess
from unittest.mock import patch, MagicMock
from vpn_sentinel_common.version import get_version, get_commit_hash, get_version_info


class TestGetVersion:
    """Tests for get_version() function."""

    def test_get_version_from_env(self):
        """Test version is read from VERSION environment variable."""
        with patch.dict('os.environ', {'VERSION': '2.5.1'}):
            version = get_version()
            assert version == '2.5.1'

    def test_get_version_with_commit_hash(self):
        """Test version generation with git commit hash."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('vpn_sentinel_common.version.get_commit_hash', return_value='abc1234'):
                version = get_version()
                assert version == '1.0.0-dev-abc1234'

    def test_get_version_without_commit_hash(self):
        """Test version fallback when no commit hash available."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('vpn_sentinel_common.version.get_commit_hash', return_value=None):
                version = get_version()
                assert version == '1.0.0-dev'

    def test_get_version_empty_string_uses_git(self):
        """Test empty VERSION env variable falls back to git."""
        with patch.dict('os.environ', {'VERSION': ''}):
            with patch('vpn_sentinel_common.version.get_commit_hash', return_value='def5678'):
                version = get_version()
                # Empty string is falsy, should use git
                assert version == '1.0.0-dev-def5678'

    def test_get_version_prerelease(self):
        """Test version with prerelease tag."""
        with patch.dict('os.environ', {'VERSION': '3.0.0-rc1'}):
            version = get_version()
            assert version == '3.0.0-rc1'


class TestGetCommitHash:
    """Tests for get_commit_hash() function."""

    def test_get_commit_hash_from_env(self):
        """Test commit hash from COMMIT_HASH environment variable."""
        with patch.dict('os.environ', {'COMMIT_HASH': 'abc123def456'}):
            commit = get_commit_hash()
            assert commit == 'abc123d'  # First 7 characters

    def test_get_commit_hash_from_env_short(self):
        """Test short commit hash (less than 7 chars) is returned as-is."""
        with patch.dict('os.environ', {'COMMIT_HASH': 'abc'}):
            commit = get_commit_hash()
            assert commit == 'abc'

    def test_get_commit_hash_from_git_command(self):
        """Test commit hash retrieval via git command."""
        with patch.dict('os.environ', {}, clear=True):
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = 'fedcba9\n'
            
            with patch('subprocess.run', return_value=mock_result) as mock_run:
                commit = get_commit_hash()
                assert commit == 'fedcba9'
                mock_run.assert_called_once_with(
                    ['git', 'rev-parse', '--short=7', 'HEAD'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )

    def test_get_commit_hash_git_failure(self):
        """Test commit hash returns None when git command fails."""
        with patch.dict('os.environ', {}, clear=True):
            mock_result = MagicMock()
            mock_result.returncode = 1
            
            with patch('subprocess.run', return_value=mock_result):
                commit = get_commit_hash()
                assert commit is None

    def test_get_commit_hash_git_exception(self):
        """Test commit hash returns None when subprocess raises exception."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('git', 2)):
                commit = get_commit_hash()
                assert commit is None

    def test_get_commit_hash_git_file_not_found(self):
        """Test commit hash returns None when git is not installed."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('subprocess.run', side_effect=FileNotFoundError()):
                commit = get_commit_hash()
                assert commit is None

    def test_get_commit_hash_no_git_repo(self):
        """Test commit hash returns None when not in a git repository."""
        with patch.dict('os.environ', {}, clear=True):
            mock_result = MagicMock()
            mock_result.returncode = 128  # Git error code for not a repository
            
            with patch('subprocess.run', return_value=mock_result):
                commit = get_commit_hash()
                assert commit is None


class TestGetVersionInfo:
    """Tests for get_version_info() function."""

    def test_get_version_info_complete(self):
        """Test version info with all fields populated."""
        with patch.dict('os.environ', {
            'VERSION': '1.2.3',
            'COMMIT_HASH': 'abc123def',
            'ENVIRONMENT': 'staging'
        }):
            info = get_version_info()
            assert info['version'] == '1.2.3'
            assert info['commit'] == 'abc123d'
            assert info['environment'] == 'staging'

    def test_get_version_info_defaults(self):
        """Test version info with default values."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('vpn_sentinel_common.version.get_commit_hash', return_value=None):
                info = get_version_info()
                assert info['version'] == '1.0.0-dev'
                assert info['commit'] == 'unknown'
                assert info['environment'] == 'production'

    def test_get_version_info_production(self):
        """Test version info in production environment."""
        with patch.dict('os.environ', {
            'VERSION': '2.0.0',
            'ENVIRONMENT': 'production'
        }):
            with patch('vpn_sentinel_common.version.get_commit_hash', return_value='xyz789'):
                info = get_version_info()
                assert info['version'] == '2.0.0'
                assert info['commit'] == 'xyz789'
                assert info['environment'] == 'production'

    def test_get_version_info_development(self):
        """Test version info in development environment."""
        with patch.dict('os.environ', {'ENVIRONMENT': 'development'}):
            with patch('vpn_sentinel_common.version.get_commit_hash', return_value='dev123'):
                info = get_version_info()
                assert info['version'] == '1.0.0-dev-dev123'
                assert info['commit'] == 'dev123'
                assert info['environment'] == 'development'

    def test_get_version_info_is_dict(self):
        """Test version info returns a dictionary."""
        info = get_version_info()
        assert isinstance(info, dict)
        assert 'version' in info
        assert 'commit' in info
        assert 'environment' in info

    def test_get_version_info_unknown_commit(self):
        """Test version info shows 'unknown' when commit unavailable."""
        with patch.dict('os.environ', {'VERSION': '1.5.0'}, clear=True):
            with patch('vpn_sentinel_common.version.get_commit_hash', return_value=None):
                info = get_version_info()
                assert info['commit'] == 'unknown'


class TestVersionIntegration:
    """Integration tests for version module."""

    def test_version_consistency(self):
        """Test that version info contains consistent data."""
        info = get_version_info()
        version = get_version()
        
        # Version from get_version_info should match get_version
        assert info['version'] == version

    def test_commit_consistency(self):
        """Test that commit hash is consistent across calls."""
        with patch.dict('os.environ', {'COMMIT_HASH': 'test123456'}):
            commit1 = get_commit_hash()
            commit2 = get_commit_hash()
            info = get_version_info()
            
            assert commit1 == commit2
            assert info['commit'] == commit1

    def test_environment_override(self):
        """Test environment variable override behavior."""
        # First call with one environment
        with patch.dict('os.environ', {'ENVIRONMENT': 'test'}):
            info1 = get_version_info()
            assert info1['environment'] == 'test'
        
        # Second call with different environment
        with patch.dict('os.environ', {'ENVIRONMENT': 'prod'}):
            info2 = get_version_info()
            assert info2['environment'] == 'prod'
