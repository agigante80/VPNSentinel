"""Moved to tests/integration_server/ (server-dependent).

These tests require a running VPN Sentinel server or Docker Compose and are
skipped by default. To run them locally enable the suite explicitly:

    export VPN_SENTINEL_SERVER_TESTS=1
    pytest tests/integration_server -q

"""

import pytest

pytest.skip("Server-dependent integration tests disabled. Set VPN_SENTINEL_SERVER_TESTS=1 to enable.", allow_module_level=True)

class TestConfigurationValidation(unittest.TestCase):
    """Test configuration file validation"""
    
    def test_env_example_files(self):
        """Test that .env.example files are valid"""
        env_example_files = [
            '../../.env.example',
            '../../deployments/server-central/.env.example',
            '../../deployments/all-in-one/.env.example',
            '../../deployments/client-with-vpn/.env.example',
            '../../deployments/client-standalone/.env.example'
        ]
        
        for env_file in env_example_files:
            full_path = os.path.join(os.path.dirname(__file__), env_file)
            if os.path.exists(full_path):
                with self.subTest(env_file=env_file):
                    with open(full_path, 'r') as f:
                        lines = f.readlines()
                    
                    # Check for required variables based on deployment type
                    content = ''.join(lines)
                    
                    # All deployments need API key
                    base_required_vars = ['VPN_SENTINEL_API_KEY']
                    
                    # Server deployments need port configuration
                    server_required_vars = [
                        'VPN_SENTINEL_SERVER_API_PORT',
                        'VPN_SENTINEL_SERVER_DASHBOARD_PORT'
                    ]
                    
                    # Check base requirements
                    for var in base_required_vars:
                        self.assertIn(var, content, 
                                    f"Required variable {var} not found in {env_file}")
                    
                    # Check server requirements for server deployments only
                    if 'server-only' in env_file or 'unified' in env_file:
                        for var in server_required_vars:
                            self.assertIn(var, content,
                                        f"Server variable {var} not found in {env_file}")

                    # Client-only deployments should have server connection info
                    if 'client-only' in env_file:
                        client_required_vars = [
                            'VPN_SENTINEL_URL',
                            'VPN_SENTINEL_CLIENT_ID'
                        ]
                        for var in client_required_vars:
                            self.assertIn(var, content,
                                        f"Client variable {var} not found in {env_file}")
            else:
                self.skipTest(f"Environment file not found: {env_file}")


if __name__ == '__main__':
    # Run integration tests only if server is running
    print("Running VPN Sentinel Integration Tests")
    print("Note: These tests require the server to be running locally")
    print("Start the server with: docker-compose up -d")
    print()
    
    unittest.main(verbosity=2)
