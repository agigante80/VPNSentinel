"""Isolated tests for Telegram configuration validation.

These tests must run in isolation to avoid module state conflicts.
They test the initialization logic by using subprocess.
"""
import subprocess
import os


class TestTelegramValidationIsolated:
    """Tests for Telegram configuration validation in isolated processes."""
    
    def test_telegram_enabled_without_token_exits(self):
        """Test that VPN_SENTINEL_TELEGRAM_ENABLED=true without token causes exit."""
        env = os.environ.copy()
        env.update({
            'VPN_SENTINEL_TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': '',
            'TELEGRAM_CHAT_ID': '',
            'PYTHONPATH': os.getcwd()
        })
        
        result = subprocess.run([
            'python', '-c', 'from vpn_sentinel_common import telegram'
        ], env=env, capture_output=True, cwd=os.getcwd())
        
        assert result.returncode == 1
    
    def test_telegram_enabled_without_chat_id_exits(self):
        """Test that VPN_SENTINEL_TELEGRAM_ENABLED=true without chat ID causes exit."""
        env = os.environ.copy()
        env.update({
            'VPN_SENTINEL_TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': 'test-token',
            'TELEGRAM_CHAT_ID': '',
            'PYTHONPATH': os.getcwd()
        })
        
        result = subprocess.run([
            'python', '-c', 'from vpn_sentinel_common import telegram'
        ], env=env, capture_output=True, cwd=os.getcwd())
        
        assert result.returncode == 1
    
    def test_telegram_enabled_with_credentials_succeeds(self):
        """Test that VPN_SENTINEL_TELEGRAM_ENABLED=true with credentials works."""
        env = os.environ.copy()
        env.update({
            'VPN_SENTINEL_TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': 'test-token-123',
            'TELEGRAM_CHAT_ID': '123456789',
            'PYTHONPATH': os.getcwd()
        })
        
        # Test that import succeeds (no sys.exit)
        result = subprocess.run([
            'python', '-c', 
            'from vpn_sentinel_common import telegram; '
            'print(f"enabled={telegram.TELEGRAM_ENABLED}"); '
            'print(f"token={telegram.TELEGRAM_BOT_TOKEN}"); '
            'print(f"chat={telegram.TELEGRAM_CHAT_ID}")'
        ], env=env, capture_output=True, text=True, cwd=os.getcwd())
        
        assert result.returncode == 0
        assert 'enabled=True' in result.stdout
        assert 'token=test-token-123' in result.stdout
        assert 'chat=123456789' in result.stdout
    
    def test_telegram_explicit_disable(self):
        """Test that VPN_SENTINEL_TELEGRAM_ENABLED=false disables even with credentials."""
        env = os.environ.copy()
        env.update({
            'VPN_SENTINEL_TELEGRAM_ENABLED': 'false',
            'TELEGRAM_BOT_TOKEN': 'test-token',
            'TELEGRAM_CHAT_ID': '123456',
            'PYTHONPATH': os.getcwd()
        })
        
        result = subprocess.run([
            'python', '-c', 
            'from vpn_sentinel_common import telegram; '
            'print(f"enabled={telegram.TELEGRAM_ENABLED}")'
        ], env=env, capture_output=True, text=True, cwd=os.getcwd())
        
        assert result.returncode == 0
        assert 'enabled=False' in result.stdout
    
    def test_telegram_auto_enable_with_credentials(self):
        """Test that Telegram auto-enables when credentials present (no explicit flag)."""
        env = os.environ.copy()
        env.update({
            'TELEGRAM_BOT_TOKEN': 'test-token-456',
            'TELEGRAM_CHAT_ID': '987654321',
            'PYTHONPATH': os.getcwd()
        })
        # Remove explicit flag if present
        env.pop('VPN_SENTINEL_TELEGRAM_ENABLED', None)
        
        result = subprocess.run([
            'python', '-c', 
            'from vpn_sentinel_common import telegram; '
            'print(f"enabled={telegram.TELEGRAM_ENABLED}")'
        ], env=env, capture_output=True, text=True, cwd=os.getcwd())
        
        assert result.returncode == 0
        assert 'enabled=True' in result.stdout