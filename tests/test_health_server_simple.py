#!/usr/bin/env python3
"""
Simple test script to verify dedicated health port functionality
"""
import os
import sys
import json

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'vpn-sentinel-server'))

def test_health_app():
    """Test the health app functionality"""
    try:
        # Try direct import first
        try:
            from vpn_sentinel_server import health_app
        except ImportError:
            # Use importlib as fallback
            import importlib.util
            server_path = os.path.join(os.path.dirname(__file__), '..', 'vpn-sentinel-server', 'vpn-sentinel-server.py')
            spec = importlib.util.spec_from_file_location('vpn_sentinel_server', server_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            health_app = module.health_app

        # Configure for testing
        health_app.config['TESTING'] = True
        client = health_app.test_client()

        print("🧪 Testing Dedicated Health Port Functionality")
        print("=" * 50)

        # Test main health endpoint
        print("1. Testing /health endpoint...")
        response = client.get('/health')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = json.loads(response.data)
        assert data['status'] == 'healthy', f"Expected 'healthy', got {data['status']}"
        assert 'server_time' in data, "server_time not in response"
        assert 'system' in data, "system not in response"
        print("   ✅ /health endpoint works correctly")

        # Test readiness endpoint
        print("2. Testing /health/ready endpoint...")
        response = client.get('/health/ready')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = json.loads(response.data)
        assert data['status'] == 'ready', f"Expected 'ready', got {data['status']}"
        assert 'checks' in data, "checks not in response"
        print("   ✅ /health/ready endpoint works correctly")

        # Test startup endpoint
        print("3. Testing /health/startup endpoint...")
        response = client.get('/health/startup')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = json.loads(response.data)
        assert data['status'] == 'started', f"Expected 'started', got {data['status']}"
        assert 'server_time' in data, "server_time not in response"
        print("   ✅ /health/startup endpoint works correctly")

        # Test wrong methods
        print("4. Testing wrong HTTP methods...")
        response = client.post('/health')
        assert response.status_code == 405, f"Expected 405, got {response.status_code}"
        print("   ✅ Wrong methods properly rejected")

        # Test invalid paths
        print("5. Testing invalid paths...")
        response = client.get('/health/invalid')
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("   ✅ Invalid paths properly rejected")

        print("\n" + "=" * 50)
        print("🎉 All health server tests passed!")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_health_app()
    sys.exit(0 if success else 1)