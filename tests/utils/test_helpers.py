"""
Test utilities for VPN Sentinel project
"""
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import Mock, patch
import pytest


class MockEnvironment:
    """Context manager for mocking environment variables"""
    
    def __init__(self, **env_vars):
        self.env_vars = env_vars
        self.original_env = {}
    
    def __enter__(self):
        for key, value in self.env_vars.items():
            self.original_env[key] = os.environ.get(key)
            os.environ[key] = str(value)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        for key in self.env_vars:
            if self.original_env[key] is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = self.original_env[key]


def create_test_env():
    """Create test environment variables"""
    return {
        'VPN_SENTINEL_API_KEY': 'test-api-key-12345',
        'VPN_SENTINEL_SERVER_API_PORT': '5000',
        'VPN_SENTINEL_SERVER_DASHBOARD_PORT': '5553',
        'VPN_SENTINEL_SERVER_DASHBOARD_ENABLED': 'true',
        'VPN_SENTINEL_ALERT_THRESHOLD_MINUTES': '15',
        'VPN_SENTINEL_CHECK_INTERVAL_MINUTES': '5',
        'TELEGRAM_BOT_TOKEN': 'test-bot-token',
        'TELEGRAM_CHAT_ID': 'test-chat-id',
        'TZ': 'UTC'
    }


def create_mock_client_data():
    """Create mock client data for testing"""
    return {
        'vpn-monitor-test': {
            'last_seen': datetime.now(timezone.utc),
            'client_name': 'vpn-monitor-test',
            'public_ip': '172.67.163.127',
            'status': 'alive',
            'location': {
                'country': 'ES',
                'city': 'Madrid',
                'region': 'Madrid',
                'org': 'AS57269 DIGI SPAIN TELECOM S.L.',
                'timezone': 'Europe/Madrid'
            },
            'dns_test': {
                'location': 'ES',
                'colo': 'MAD'
            }
        },
        'vpn-monitor-main': {
            'last_seen': datetime.now(timezone.utc),
            'client_name': 'vpn-monitor-main',
            'public_ip': '140.82.121.4',
            'status': 'alive',
            'location': {
                'country': 'PL',
                'city': 'Toruń',
                'region': 'Kujawsko-Pomorskie',
                'org': 'AS50599 DATASPACE P.S.A.',
                'timezone': 'Europe/Warsaw'
            },
            'dns_test': {
                'location': 'PL',
                'colo': 'WAW'
            }
        }
    }


def create_mock_request():
    """Create a mock Flask request object"""
    mock_request = Mock()
    mock_request.headers = {
        'X-Forwarded-For': '127.0.0.1',
        'User-Agent': 'pytest-test-agent',
        'Authorization': 'Bearer test-api-key-12345'
    }
    mock_request.remote_addr = '127.0.0.1'
    mock_request.path = '/test'
    mock_request.get_json.return_value = {
        'client_id': 'test-client',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'public_ip': '1.2.3.4',
        'status': 'alive',
        'location': {
            'country': 'US',
            'city': 'New York',
            'region': 'New York',
            'org': 'AS12345 Test Provider',
            'timezone': 'America/New_York'
        },
        'dns_test': {
            'location': 'US',
            'colo': 'NYC'
        }
    }
    return mock_request


@pytest.fixture
def mock_env():
    """Pytest fixture for mocked environment"""
    with MockEnvironment(**create_test_env()):
        yield


@pytest.fixture
def mock_clients():
    """Pytest fixture for mock client data"""
    return create_mock_client_data()


@pytest.fixture
def temp_log_file():
    """Create temporary log file for testing"""
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.log') as f:
        yield f.name
    os.unlink(f.name)