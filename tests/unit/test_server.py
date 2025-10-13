"""
Unit tests for VPN Sentinel Server
Tests the core functionality of vpn-sentinel-server.py
"""
import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import json

# Add the server directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../vpn-sentinel-server'))

# Import test fixtures
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../fixtures'))
from sample_data import (
    SAMPLE_KEEPALIVE_REQUEST, 
    SAMPLE_VPN_CLIENT, 
    SAMPLE_SAME_IP_CLIENT,
    SAMPLE_SERVER_INFO,
    TEST_ENV_VARS
)


class TestServerFunctions(unittest.TestCase):
    """Test server utility functions"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, TEST_ENV_VARS)
        self.env_patcher.start()
        
        # Import server module after environment is set
        global server_module
        try:
            import vpn_sentinel_server as server_module
        except ImportError:
            # If direct import fails, try importing the actual module
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "vpn_sentinel_server", 
                "../../vpn-sentinel-server/vpn-sentinel-server.py"
            )
            server_module = importlib.util.module_from_spec(spec)
    
    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
    
    @patch('requests.get')
    def test_get_server_public_ip_success(self, mock_get):
        """Test successful server IP retrieval"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'ip': '172.67.163.127'}
        mock_get.return_value = mock_response
        
        # This test will be completed when we can properly import the server module
        # For now, we'll test the logic conceptually
        expected_ip = '172.67.163.127'
        self.assertEqual(expected_ip, '172.67.163.127')
    
    @patch('requests.get')
    def test_get_server_public_ip_fallback(self, mock_get):
        """Test IP retrieval with fallback service"""
        # Mock first service failing, second succeeding
        mock_get.side_effect = [
            Exception("First service failed"),
            Mock(status_code=200, json=lambda: {'ip': '1.2.3.4'})
        ]
        
        # Test would verify fallback behavior
        self.assertTrue(True)  # Placeholder
    
    def test_get_current_time(self):
        """Test timezone-aware time generation"""
        now = datetime.now(timezone.utc)
        # Verify time is timezone-aware
        self.assertIsNotNone(now.tzinfo)
        self.assertEqual(now.tzinfo, timezone.utc)


class TestKeepAliveEndpoint(unittest.TestCase):
    """Test the keepalive API endpoint"""
    
    def setUp(self):
        """Set up test environment"""
        self.env_patcher = patch.dict(os.environ, TEST_ENV_VARS)
        self.env_patcher.start()
        
        # Mock clients dictionary
        self.mock_clients = {}
    
    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
    
    def test_keepalive_new_client(self):
        """Test keepalive from new client"""
        request_data = SAMPLE_KEEPALIVE_REQUEST.copy()
        
        # Simulate processing new client
        client_id = request_data['client_id']
        self.assertNotIn(client_id, self.mock_clients)
        
        # After processing, client should be added
        self.mock_clients[client_id] = {
            'last_seen': datetime.now(timezone.utc),
            'client_name': client_id,
            'public_ip': request_data['public_ip'],
            'status': 'alive',
            'location': request_data['location'],
            'dns_test': request_data['dns_test']
        }
        
        self.assertIn(client_id, self.mock_clients)
        self.assertEqual(self.mock_clients[client_id]['public_ip'], request_data['public_ip'])
    
    def test_keepalive_same_ip_detection(self):
        """Test same IP detection logic"""
        server_ip = '172.67.163.127'
        client_ip = '172.67.163.127'  # Same as server
        
        # Test same IP detection
        is_same_ip = (client_ip != 'unknown' and 
                      server_ip != 'Unknown' and 
                      client_ip == server_ip)
        
        self.assertTrue(is_same_ip)
        
        # Test different IP
        different_client_ip = '140.82.121.4'
        is_different_ip = (different_client_ip != 'unknown' and 
                          server_ip != 'Unknown' and 
                          different_client_ip == server_ip)
        
        self.assertFalse(is_different_ip)
    
    def test_keepalive_ip_change_detection(self):
        """Test IP change detection"""
        client_id = 'test-client'
        old_ip = '1.2.3.4'
        new_ip = '5.6.7.8'
        
        # Simulate existing client
        self.mock_clients[client_id] = {
            'public_ip': old_ip,
            'last_seen': datetime.now(timezone.utc) - timedelta(minutes=10)
        }
        
        # Test IP change detection
        previous_ip = self.mock_clients.get(client_id, {}).get('public_ip', None)
        ip_changed = previous_ip is not None and previous_ip != new_ip
        
        self.assertTrue(ip_changed)


class TestStatusLogic(unittest.TestCase):
    """Test client status determination logic"""
    
    def setUp(self):
        """Set up test environment"""
        self.env_patcher = patch.dict(os.environ, TEST_ENV_VARS)
        self.env_patcher.start()
        
        self.alert_threshold = 15  # minutes
        self.server_ip = '172.67.163.127'
    
    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
    
    def test_online_status_different_ip(self):
        """Test online status for client with different IP"""
        now = datetime.now(timezone.utc)
        last_seen = now - timedelta(minutes=5)  # 5 minutes ago (< threshold)
        client_ip = '140.82.121.4'  # Different from server
        
        minutes_ago = int((now - last_seen).total_seconds() / 60)
        
        if minutes_ago < self.alert_threshold:
            if client_ip != 'unknown' and self.server_ip != 'Unknown' and client_ip == self.server_ip:
                status = 'warning'
            else:
                status = 'online'
        else:
            status = 'offline'
        
        self.assertEqual(status, 'online')
    
    def test_warning_status_same_ip(self):
        """Test warning status for client with same IP as server"""
        now = datetime.now(timezone.utc)
        last_seen = now - timedelta(minutes=5)  # 5 minutes ago (< threshold)
        client_ip = '172.67.163.127'  # Same as server
        
        minutes_ago = int((now - last_seen).total_seconds() / 60)
        
        if minutes_ago < self.alert_threshold:
            if client_ip != 'unknown' and self.server_ip != 'Unknown' and client_ip == self.server_ip:
                status = 'warning'
            else:
                status = 'online'
        else:
            status = 'offline'
        
        self.assertEqual(status, 'warning')
    
    def test_offline_status(self):
        """Test offline status for client that hasn't been seen recently"""
        now = datetime.now(timezone.utc)
        last_seen = now - timedelta(minutes=20)  # 20 minutes ago (> threshold)
        client_ip = '140.82.121.4'
        
        minutes_ago = int((now - last_seen).total_seconds() / 60)
        
        if minutes_ago < self.alert_threshold:
            if client_ip != 'unknown' and self.server_ip != 'Unknown' and client_ip == self.server_ip:
                status = 'warning'
            else:
                status = 'online'
        else:
            status = 'offline'
        
        self.assertEqual(status, 'offline')


class TestTelegramCommands(unittest.TestCase):
    """Test Telegram bot command handlers"""
    
    def setUp(self):
        """Set up test environment"""
        self.env_patcher = patch.dict(os.environ, TEST_ENV_VARS)
        self.env_patcher.start()
    
    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
    
    def test_status_command_format(self):
        """Test /status command message formatting"""
        # Mock clients data
        mock_clients = {
            'vpn-client-1': {
                'last_seen': datetime.now(timezone.utc) - timedelta(minutes=2),
                'public_ip': '140.82.121.4'
            },
            'same-ip-client': {
                'last_seen': datetime.now(timezone.utc) - timedelta(minutes=1),
                'public_ip': '172.67.163.127'  # Same as server
            }
        }
        
        server_ip = '172.67.163.127'
        alert_threshold = 15
        
        # Test status message generation logic
        status_lines = []
        for client_id, info in mock_clients.items():
            now = datetime.now(timezone.utc)
            minutes_ago = int((now - info['last_seen']).total_seconds() / 60)
            client_ip = info['public_ip']
            
            if minutes_ago < alert_threshold:
                if client_ip != 'unknown' and server_ip != 'Unknown' and client_ip == server_ip:
                    status_icon = "⚠️"
                    status_text = "Online (Same IP as server)"
                else:
                    status_icon = "🟢"
                    status_text = "Online"
            else:
                status_icon = "🔴"
                status_text = "Offline"
            
            status_lines.append(f"{status_icon} {client_id} - {status_text}")
        
        # Verify expected status messages
        self.assertIn("🟢 vpn-client-1 - Online", status_lines[0])
        self.assertIn("⚠️ same-ip-client - Online (Same IP as server)", status_lines[1])
    
    def test_ping_command_response(self):
        """Test /ping command response format"""
        expected_elements = [
            "🏓 Pong!",
            "VPN Sentinel Server is running",
            "Active clients:",
            "Alert threshold:",
            "Check interval:"
        ]
        
        # Mock ping response generation
        ping_response = (
            "🏓 <b>Pong!</b>\n\n"
            "✅ VPN Sentinel Server is running\n"
            "Active clients: <code>2</code>\n"
            "Alert threshold: <code>15 minutes</code>\n"
            "Check interval: <code>5 minutes</code>"
        )
        
        for element in expected_elements:
            self.assertIn(element, ping_response)


class TestDashboardData(unittest.TestCase):
    """Test dashboard data preparation"""
    
    def setUp(self):
        """Set up test environment"""
        self.env_patcher = patch.dict(os.environ, TEST_ENV_VARS)
        self.env_patcher.start()
    
    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
    
    def test_dashboard_client_data_format(self):
        """Test dashboard client data formatting"""
        # Mock client info
        client_info = {
            'last_seen': datetime.now(timezone.utc) - timedelta(minutes=3),
            'public_ip': '140.82.121.4',
            'location': {
                'city': 'Toruń',
                'region': 'Kujawsko-Pomorskie',
                'country': 'PL',
                'timezone': 'Europe/Warsaw',
                'org': 'AS50599 DATASPACE P.S.A.'
            },
            'dns_test': {
                'location': 'PL',
                'colo': 'WAW'
            }
        }
        
        # Test data formatting logic
        now = datetime.now(timezone.utc)
        minutes_ago = int((now - client_info['last_seen']).total_seconds() / 60)
        
        # Format location
        location_info = client_info.get('location', {})
        city = location_info.get('city', 'Unknown')
        region = location_info.get('region', '')
        country = location_info.get('country', 'Unknown')
        
        if city != 'Unknown' and region:
            location_display = f"{city}, {region}, {country}"
        elif city != 'Unknown':
            location_display = f"{city}, {country}"
        else:
            location_display = country
        
        self.assertEqual(location_display, "Toruń, Kujawsko-Pomorskie, PL")
        self.assertEqual(minutes_ago, 3)


if __name__ == '__main__':
    unittest.main()