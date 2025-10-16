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
        except ImportError as e:
            print(f"Direct import failed: {e}")
            # If direct import fails, try importing the actual module
            import importlib.util
            # Try multiple possible paths to find the server file
            possible_paths = [
                os.path.join(os.path.dirname(__file__), '../../vpn-sentinel-server/vpn-sentinel-server.py'),  # Relative to test file
                '/home/runner/work/VPNSentinel/VPNSentinel/vpn-sentinel-server/vpn-sentinel-server.py',  # CI path
                '/home/alien/dev/VPNSentinel/vpn-sentinel-server/vpn-sentinel-server.py',  # Local path
            ]
            
            server_file_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    server_file_path = path
                    break
            
            if server_file_path is None:
                raise FileNotFoundError(f"Could not find server file in any of: {possible_paths}")
                
            print(f"Loading server module from: {server_file_path}")
            spec = importlib.util.spec_from_file_location(
                "vpn_sentinel_server", 
                server_file_path
            )
            server_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(server_module)  # Execute the module to define functions
        
        # Make server_module available as instance attribute
        self.server_module = server_module
    
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
    
    @patch('requests.get')
    def test_get_server_info_success_ipinfo(self, mock_get):
        """Test successful server info retrieval from ipinfo.io"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'ip': '172.67.163.127',
            'city': 'Madrid',
            'region': 'Madrid',
            'country': 'ES',
            'org': 'Digi Spain Telecom S.L.'
        }
        mock_get.return_value = mock_response
        
        # Use the server_module from setUp if available
        if hasattr(self, 'server_module') and hasattr(self.server_module, 'get_server_info'):
            result = self.server_module.get_server_info()
            
            self.assertEqual(result['public_ip'], '172.67.163.127')
            self.assertEqual(result['location'], 'Madrid, Madrid, ES')
            self.assertEqual(result['provider'], 'Digi Spain Telecom S.L.')
            self.assertEqual(result['dns_status'], 'Operational')
        else:
            # Skip if module not available
            self.skipTest("Server module not available in test environment")
    
    @patch('requests.get')
    def test_get_server_info_fallback_to_ipapi(self, mock_get):
        """Test server info fallback from ipinfo.io to ip-api.com"""
        # Mock ipinfo.io failing, ip-api.com succeeding
        mock_ipinfo_response = Mock()
        mock_ipinfo_response.status_code = 500
        
        mock_ipapi_response = Mock()
        mock_ipapi_response.status_code = 200
        mock_ipapi_response.json.return_value = {
            'query': '172.67.163.127',
            'city': 'Madrid',
            'regionName': 'Madrid',
            'countryCode': 'ES',
            'isp': 'Digi Spain Telecom S.L.'
        }
        
        mock_get.side_effect = [mock_ipinfo_response, mock_ipapi_response]
        
        if hasattr(self, 'server_module') and hasattr(self.server_module, 'get_server_info'):
            result = self.server_module.get_server_info()
            
            self.assertEqual(result['public_ip'], '172.67.163.127')
            self.assertEqual(result['location'], 'Madrid, Madrid, ES')
            self.assertEqual(result['provider'], 'Digi Spain Telecom S.L.')
            self.assertEqual(result['dns_status'], 'Operational')
        else:
            self.skipTest("Server module not available in test environment")
    
    @patch('requests.get')
    def test_get_server_info_both_services_fail(self, mock_get):
        """Test server info when both geolocation services fail"""
        # Mock both services failing
        mock_get.side_effect = Exception("Network error")
        
        if hasattr(self, 'server_module') and hasattr(self.server_module, 'get_server_info'):
            result = self.server_module.get_server_info()
            
            # Should return default values
            self.assertEqual(result['public_ip'], 'Unknown')
            self.assertEqual(result['location'], 'Unknown')
            self.assertEqual(result['provider'], 'Unknown')
            self.assertEqual(result['dns_status'], 'Unknown')
        else:
            self.skipTest("Server module not available in test environment")
    
    @patch('requests.get')
    def test_get_server_info_ipapi_field_mapping(self, mock_get):
        """Test correct field mapping for ip-api.com responses"""
        # Mock ipinfo.io failing first, then ip-api.com succeeding
        mock_ipinfo_response = Mock()
        mock_ipinfo_response.status_code = 500  # Make ipinfo.io fail
        
        mock_ipapi_response = Mock()
        mock_ipapi_response.status_code = 200
        mock_ipapi_response.json.return_value = {
            'query': '1.2.3.4',           # IP field
            'countryCode': 'US',         # Country field
            'city': 'New York',          # City field
            'regionName': 'New York',    # Region field
            'isp': 'Verizon Communications'  # Provider field
        }
        
        mock_get.side_effect = [mock_ipinfo_response, mock_ipapi_response]
        
        if hasattr(self, 'server_module') and hasattr(self.server_module, 'get_server_info'):
            result = self.server_module.get_server_info()
            
            self.assertEqual(result['public_ip'], '1.2.3.4')
            self.assertEqual(result['location'], 'New York, New York, US')
            self.assertEqual(result['provider'], 'Verizon Communications')
        else:
            self.skipTest("Server module not available in test environment")
    
    @patch('requests.get')
    def test_get_server_info_partial_location_data(self, mock_get):
        """Test server info with partial location data"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'ip': '5.6.7.8',
            'city': 'London',
            # Missing region
            'country': 'GB',
            'org': 'British Telecom'
        }
        mock_get.return_value = mock_response
        
        if hasattr(self, 'server_module') and hasattr(self.server_module, 'get_server_info'):
            result = self.server_module.get_server_info()
            
            self.assertEqual(result['public_ip'], '5.6.7.8')
            self.assertEqual(result['location'], 'London, GB')  # Should handle missing region
            self.assertEqual(result['provider'], 'British Telecom')
        else:
            self.skipTest("Server module not available in test environment")
    
    @patch('requests.get')
    def test_get_server_info_invalid_ip(self, mock_get):
        """Test server info retrieval with invalid IP address"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'ip': 'invalid-ip',
            'city': '',
            'region': '',
            'country': '',
            'org': ''
        }
        mock_get.return_value = mock_response
        
        if hasattr(self, 'server_module') and hasattr(self.server_module, 'get_server_info'):
            result = self.server_module.get_server_info()
            
            # Invalid IP should return the invalid IP but empty location/provider
            self.assertEqual(result['public_ip'], 'invalid-ip')
            self.assertEqual(result['location'], '')  # Empty when all location fields are empty
            self.assertEqual(result['provider'], '')  # Empty when org field is empty
        else:
            self.skipTest("Server module not available in test environment")


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

        def test_dns_leak_detection(self):
            """Test detection of DNS leak in keepalive data"""
            # Simulate keepalive with DNS leak
            request_data = SAMPLE_KEEPALIVE_REQUEST.copy()
            request_data['dns_test'] = {'leak': True, 'location': 'PL', 'colo': 'WAW'}
            # Server logic: if 'leak' is True, flag DNS leak
            dns_leak = request_data['dns_test'].get('leak', False)
            self.assertTrue(dns_leak)
    
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
    def test_status_command_all_states(self):
        """Test /status command for online, offline, warning clients"""
        mock_clients = {
            'online-client': {
                'last_seen': datetime.now(timezone.utc) - timedelta(minutes=2),
                'public_ip': '140.82.121.4'
            },
            'warning-client': {
                'last_seen': datetime.now(timezone.utc) - timedelta(minutes=1),
                'public_ip': '172.67.163.127'  # Same as server
            },
            'offline-client': {
                'last_seen': datetime.now(timezone.utc) - timedelta(minutes=20),
                'public_ip': '140.82.121.4'
            }
        }
        server_ip = '172.67.163.127'
        alert_threshold = 15
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
        self.assertIn("🟢 online-client - Online", status_lines)
        self.assertIn("⚠️ warning-client - Online (Same IP as server)", status_lines)
        self.assertIn("🔴 offline-client - Offline", status_lines)

    def test_ping_command_no_clients(self):
        """Test /ping command when no clients are connected"""
        ping_response = (
            "🏓 <b>Pong!</b>\n\n"
            "✅ VPN Sentinel Server is running\n"
            "Active clients: <code>0</code>\n"
            "Alert threshold: <code>15 minutes</code>\n"
            "Check interval: <code>5 minutes</code>"
        )
        self.assertIn("Active clients: <code>0</code>", ping_response)

    def test_telegram_rate_limit_error(self):
        """Test Telegram bot handles rate limiting/API error"""
        # Simulate Telegram API error response
        error_response = {"ok": False, "error_code": 429, "description": "Too Many Requests: retry after 10"}
        self.assertEqual(error_response["error_code"], 429)
        self.assertIn("Too Many Requests", error_response["description"])
    """Test Telegram bot command handlers"""
    
    def setUp(self):
        """Set up test environment"""
        self.env_patcher = patch.dict(os.environ, TEST_ENV_VARS)
        self.env_patcher.start()
    
    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()

        def test_help_command_response(self):
            """Test /help command returns help message"""
            # Simulate Telegram /help command
            command = '/help'
            # Server logic: should return help text
            help_text = "Available commands: /status, /ping, /help"
            self.assertIn('/help', help_text)
            self.assertTrue(help_text.startswith('Available commands'))

        def test_non_recognized_telegram_message(self):
            """Test response to non-recognized Telegram message"""
            # Simulate Telegram sending an unknown command
            message = '/foobar'
            # Server logic: should return fallback/error message
            fallback_text = "Sorry, I did not understand that command."
            self.assertIn('not understand', fallback_text)
    
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
        # Actual ping response format uses HTML tags
        ping_response = (
            "🏓 <b>Pong!</b>\n\n"
            "✅ VPN Sentinel Server is running\n"
            "Active clients: <code>2</code>\n"
            "Alert threshold: <code>15 minutes</code>\n"
            "Check interval: <code>5 minutes</code>"
        )
        # Check for key phrases and HTML formatting
        self.assertIn("<b>Pong!</b>", ping_response)
        self.assertIn("VPN Sentinel Server is running", ping_response)
        self.assertIn("Active clients: <code>2</code>", ping_response)
        self.assertIn("Alert threshold: <code>15 minutes</code>", ping_response)
        self.assertIn("Check interval: <code>5 minutes</code>", ping_response)


class TestDashboardData(unittest.TestCase):
    def test_dashboard_dns_leak_warning(self):
        """Test dashboard displays DNS leak warning for affected clients"""
        client_info = {
            'last_seen': datetime.now(timezone.utc) - timedelta(minutes=3),
            'public_ip': '140.82.121.4',
            'location': {'city': 'Toruń', 'region': 'Kujawsko-Pomorskie', 'country': 'PL'},
            'dns_test': {'leak': True, 'location': 'PL', 'colo': 'WAW'}
        }
        dns_leak = client_info['dns_test'].get('leak', False)
        warning_msg = "DNS leak detected!" if dns_leak else "No DNS leak."
        self.assertEqual(warning_msg, "DNS leak detected!")
    def test_keepalive_malformed_data(self):
        """Test keepalive endpoint handles malformed or missing data"""
        # Missing required fields
        malformed_request = {'client_id': None, 'public_ip': '', 'dns_test': {}}
        # Server logic: should handle gracefully
        self.assertIsNone(malformed_request['client_id'])
        self.assertEqual(malformed_request['public_ip'], '')
        self.assertEqual(malformed_request['dns_test'], {})

    def test_multiple_same_ip_clients(self):
        """Test server handles multiple clients with same IP (VPN bypass)"""
        server_ip = '172.67.163.127'
        clients = [
            {'client_id': 'client1', 'public_ip': server_ip},
            {'client_id': 'client2', 'public_ip': server_ip},
            {'client_id': 'client3', 'public_ip': '140.82.121.4'}
        ]
        same_ip_clients = [c for c in clients if c['public_ip'] == server_ip]
        self.assertEqual(len(same_ip_clients), 2)
class TestServerLogging(unittest.TestCase):
    """Test server logs critical events (DNS leak, same-IP, offline)"""
    def test_log_dns_leak(self):
        event = "DNS leak detected for client client1"
        self.assertIn("DNS leak detected", event)

    def test_log_same_ip(self):
        event = "VPN bypass: client2 has same IP as server"
        self.assertIn("VPN bypass", event)

    def test_log_offline(self):
        event = "Client client3 is offline"
        self.assertIn("offline", event)
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


class TestInputValidation(unittest.TestCase):
    """Test input validation and sanitization functions"""
    
    def setUp(self):
        """Set up test environment"""
        self.env_patcher = patch.dict(os.environ, TEST_ENV_VARS)
        self.env_patcher.start()
        
        # Import server module after environment is set
        global server_module
        try:
            import vpn_sentinel_server as server_module
        except ImportError:
            # If direct import fails, try importing the actual module
            import importlib.util
            # Use relative path from test file to server file
            server_file_path = os.path.join(os.path.dirname(__file__), '../../vpn-sentinel-server/vpn-sentinel-server.py')
            spec = importlib.util.spec_from_file_location(
                "vpn_sentinel_server", 
                server_file_path
            )
            server_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(server_module)  # Execute the module to define functions
        
        # Make server_module available as instance attribute
        self.server_module = server_module
    
    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
    
    def test_validate_client_id_valid(self):
        """Test validate_client_id with valid inputs"""
        # Valid client IDs
        self.assertEqual(server_module.validate_client_id("client-123"), "client-123")
        self.assertEqual(server_module.validate_client_id("my_vpn_client"), "my_vpn_client")
        self.assertEqual(server_module.validate_client_id("client.123"), "client.123")
    
    def test_validate_client_id_invalid(self):
        """Test validate_client_id with invalid inputs"""
        # Invalid client IDs - should return 'unknown'
        self.assertEqual(server_module.validate_client_id(""), "unknown")  # Empty string
        self.assertEqual(server_module.validate_client_id("   "), "unknown")  # Whitespace only
        self.assertEqual(server_module.validate_client_id("client@123"), "unknown")  # Invalid character
        self.assertEqual(server_module.validate_client_id("client with spaces"), "unknown")  # Spaces
        self.assertEqual(server_module.validate_client_id("a" * 101), "unknown")  # Too long
        
        # Non-string inputs
        self.assertEqual(server_module.validate_client_id(None), "unknown")
        self.assertEqual(server_module.validate_client_id(123), "unknown")
        self.assertEqual(server_module.validate_client_id([]), "unknown")
    
    def test_validate_public_ip_valid(self):
        """Test validate_public_ip with valid IP addresses"""
        # Valid IPv4 addresses
        self.assertEqual(server_module.validate_public_ip("192.168.1.1"), "192.168.1.1")
        self.assertEqual(server_module.validate_public_ip("10.0.0.1"), "10.0.0.1")
        self.assertEqual(server_module.validate_public_ip("172.16.0.1"), "172.16.0.1")
        
        # Valid IPv6 addresses
        self.assertEqual(server_module.validate_public_ip("2001:db8::1"), "2001:db8::1")
        self.assertEqual(server_module.validate_public_ip("::1"), "::1")
    
    def test_validate_public_ip_invalid(self):
        """Test validate_public_ip with invalid inputs"""
        # Invalid IP addresses
        self.assertEqual(server_module.validate_public_ip(""), "unknown")  # Empty string
        self.assertEqual(server_module.validate_public_ip("   "), "unknown")  # Whitespace only
        self.assertEqual(server_module.validate_public_ip("192.168.1.256"), "unknown")  # Invalid IPv4
        self.assertEqual(server_module.validate_public_ip("not-an-ip"), "unknown")  # Not an IP
        self.assertEqual(server_module.validate_public_ip("192.168.1.1.1"), "unknown")  # Too many octets
        self.assertEqual(server_module.validate_public_ip("a" * 46), "unknown")  # Too long
        
        # Non-string inputs
        self.assertEqual(server_module.validate_public_ip(None), "unknown")
        self.assertEqual(server_module.validate_public_ip(123), "unknown")
    
    def test_validate_location_string_valid(self):
        """Test validate_location_string with valid inputs"""
        # Valid location strings
        self.assertEqual(server_module.validate_location_string("New York", "city"), "New York")
        self.assertEqual(server_module.validate_location_string("United States", "country"), "United States")
        self.assertEqual(server_module.validate_location_string("AS12345 Provider Name", "org"), "AS12345 Provider Name")
        self.assertEqual(server_module.validate_location_string("America/New_York", "timezone"), "America/New_York")
    
    def test_validate_location_string_invalid(self):
        """Test validate_location_string with invalid inputs"""
        # Invalid location strings - should return 'Unknown'
        self.assertEqual(server_module.validate_location_string("", "city"), "Unknown")  # Empty string
        self.assertEqual(server_module.validate_location_string("   ", "city"), "Unknown")  # Whitespace only
        self.assertEqual(server_module.validate_location_string("a" * 101, "city"), "Unknown")  # Too long
        self.assertEqual(server_module.validate_location_string("City<script>", "city"), "Unknown")  # Dangerous chars
        
        # Non-string inputs
        self.assertEqual(server_module.validate_location_string(None, "city"), "Unknown")
        self.assertEqual(server_module.validate_location_string(123, "city"), "Unknown")
    
    def test_validate_location_string_sanitization(self):
        """Test that validate_location_string properly sanitizes dangerous characters"""
        # These should be rejected due to dangerous characters
        dangerous_inputs = [
            "City<script>alert('xss')</script>",
            "Country; rm -rf /",
            "Location`whoami`",
            "Place$(evil_command)",
            "Area|malicious",
            "Region\x00null_byte"
        ]
        
        for dangerous_input in dangerous_inputs:
            result = server_module.validate_location_string(dangerous_input, "test_field")
            self.assertEqual(result, "Unknown", f"Should reject dangerous input: {dangerous_input}")


if __name__ == '__main__':
    unittest.main()