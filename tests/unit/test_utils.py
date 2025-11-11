"""
Unit tests for Utils module (utils.py)
Tests utility functions: logging, time, JSON escaping, string sanitization.
"""
import pytest
import sys
import os

# Add common library to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from vpn_sentinel_common import utils


class TestTimeLogging:
    """Tests for time and logging delegation functions."""
    
    def test_get_current_time_returns_datetime(self):
        """Test get_current_time returns a datetime object."""
        result = utils.get_current_time()
        assert result is not None
        # Should have datetime-like attributes
        assert hasattr(result, 'year')
        assert hasattr(result, 'month')
        assert hasattr(result, 'day')
    
    def test_log_functions_accept_args(self):
        """Test logging functions accept component and message."""
        # Should not raise exceptions
        utils.log_info('test', 'info message')
        utils.log_warn('test', 'warn message')
        utils.log_error('test', 'error message')


class TestJsonEscape:
    """Tests for json_escape function."""
    
    def test_json_escape_basic_string(self):
        """Test JSON escaping of basic string."""
        result = utils.json_escape('hello world')
        assert result == 'hello world'
    
    def test_json_escape_quotes(self):
        """Test JSON escaping of quotes."""
        result = utils.json_escape('say "hello"')
        assert '\\"' in result
    
    def test_json_escape_backslash(self):
        """Test JSON escaping of backslashes."""
        result = utils.json_escape('path\\to\\file')
        assert '\\\\' in result
    
    def test_json_escape_newline(self):
        """Test JSON escaping of newlines."""
        result = utils.json_escape('line1\nline2')
        assert '\\n' in result
    
    def test_json_escape_tab(self):
        """Test JSON escaping of tabs."""
        result = utils.json_escape('col1\tcol2')
        assert '\\t' in result
    
    def test_json_escape_control_characters(self):
        """Test JSON escaping of control characters."""
        result = utils.json_escape('test\x00\x01\x02')
        # Should escape control chars
        assert '\\u0000' in result or '\\x00' in result
    
    def test_json_escape_unicode(self):
        """Test JSON escaping handles unicode."""
        result = utils.json_escape('emoji: 🔒')
        assert result  # Should not crash


class TestSanitizeString:
    """Tests for sanitize_string function."""
    
    def test_sanitize_basic_string(self):
        """Test sanitizing basic string."""
        result = utils.sanitize_string('hello world')
        assert result == 'hello world'
    
    def test_sanitize_removes_control_characters(self):
        """Test control characters are removed."""
        # Add various control characters (0x00-0x1F)
        dirty = 'hello\x00\x01\x02world\x1F'
        result = utils.sanitize_string(dirty)
        assert result == 'helloworld'
        assert '\x00' not in result
        assert '\x01' not in result
    
    def test_sanitize_removes_newlines(self):
        """Test newlines are removed."""
        result = utils.sanitize_string('line1\nline2\rline3')
        assert result == 'line1line2line3'
        assert '\n' not in result
        assert '\r' not in result
    
    def test_sanitize_removes_tabs(self):
        """Test tabs are removed."""
        result = utils.sanitize_string('col1\tcol2')
        assert result == 'col1col2'
        assert '\t' not in result
    
    def test_sanitize_truncates_long_strings(self):
        """Test strings are truncated to max_len."""
        long_string = 'a' * 200
        result = utils.sanitize_string(long_string, max_len=100)
        assert len(result) == 100
    
    def test_sanitize_custom_max_len(self):
        """Test custom max_len parameter."""
        long_string = 'a' * 100
        result = utils.sanitize_string(long_string, max_len=50)
        assert len(result) == 50
    
    def test_sanitize_handles_none(self):
        """Test sanitize handles None input."""
        result = utils.sanitize_string(None)
        assert result == ''
    
    def test_sanitize_empty_string(self):
        """Test sanitize handles empty string."""
        result = utils.sanitize_string('')
        assert result == ''
    
    def test_sanitize_preserves_normal_chars(self):
        """Test normal characters are preserved."""
        text = 'ABCabc123 !@#$%^&*()_+-=[]{}:";\'<>?,./'
        result = utils.sanitize_string(text)
        # Should preserve most printable characters
        assert 'ABC' in result
        assert '123' in result
    
    def test_sanitize_removes_null_byte(self):
        """Test null bytes are specifically removed."""
        result = utils.sanitize_string('before\x00after')
        assert result == 'beforeafter'
        assert '\x00' not in result


class TestModuleExports:
    """Tests for __all__ exports."""
    
    def test_all_exports_defined(self):
        """Test __all__ contains expected functions."""
        assert 'get_current_time' in utils.__all__
        assert 'log_info' in utils.__all__
        assert 'log_warn' in utils.__all__
        assert 'log_error' in utils.__all__
        assert 'json_escape' in utils.__all__
        assert 'sanitize_string' in utils.__all__
    
    def test_all_exports_callable(self):
        """Test all exported functions are callable."""
        for name in utils.__all__:
            obj = getattr(utils, name)
            assert callable(obj), f"{name} should be callable"
