"""Integration tests for the dashboard endpoint.

Tests the dashboard web interface accessibility and functionality.
"""
import pytest
import requests
import os


@pytest.fixture
def server_base_url():
    """Get the base URL for the test server."""
    host = os.getenv('VPN_SENTINEL_SERVER_HOST', 'localhost')
    # Use mapped port for Docker test environment
    port = os.getenv('VPN_SENTINEL_SERVER_DASHBOARD_PORT', '18080')
    return f"http://{host}:{port}"


@pytest.fixture
def dashboard_url(server_base_url):
    """Get the dashboard endpoint URL."""
    return f"{server_base_url}/dashboard"


class TestDashboardEndpoint:
    """Test dashboard web interface."""

    def test_dashboard_accessible(self, dashboard_url):
        """Test that dashboard endpoint is accessible."""
        response = requests.get(dashboard_url, timeout=10)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.headers['Content-Type'].startswith('text/html')

    def test_dashboard_with_trailing_slash(self, dashboard_url):
        """Test that dashboard works with trailing slash."""
        response = requests.get(f"{dashboard_url}/", timeout=10)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.headers['Content-Type'].startswith('text/html')

    def test_dashboard_returns_html(self, dashboard_url):
        """Test that dashboard returns valid HTML."""
        response = requests.get(dashboard_url, timeout=10)
        assert response.status_code == 200
        
        html = response.text
        assert '<!DOCTYPE html>' in html or '<html>' in html
        assert '<title>' in html
        assert '</html>' in html

    def test_dashboard_contains_title(self, dashboard_url):
        """Test that dashboard contains the expected title."""
        response = requests.get(dashboard_url, timeout=10)
        assert response.status_code == 200
        
        html = response.text
        assert 'VPN Sentinel Dashboard' in html

    def test_dashboard_shows_server_status(self, dashboard_url):
        """Test that dashboard displays server status."""
        response = requests.get(dashboard_url, timeout=10)
        assert response.status_code == 200
        
        html = response.text
        # Check for status indicators
        assert 'Server Status' in html or 'Running' in html
        assert '✅' in html or 'ok' in html.lower()

    def test_dashboard_has_client_monitoring_info(self, dashboard_url):
        """Test that dashboard has client monitoring information."""
        response = requests.get(dashboard_url, timeout=10)
        assert response.status_code == 200
        
        html = response.text
        # Check for client monitoring section
        assert 'Client' in html or 'client' in html
        assert 'status' in html.lower() or 'monitoring' in html.lower()

    def test_dashboard_has_health_check_links(self, dashboard_url):
        """Test that dashboard has health check links."""
        response = requests.get(dashboard_url, timeout=10)
        assert response.status_code == 200
        
        html = response.text
        # Check for health endpoint reference
        assert '/health' in html or 'health' in html.lower()

    def test_dashboard_has_styling(self, dashboard_url):
        """Test that dashboard includes CSS styling."""
        response = requests.get(dashboard_url, timeout=10)
        assert response.status_code == 200
        
        html = response.text
        # Check for style tags or inline styles
        assert '<style>' in html or 'style=' in html

    def test_dashboard_response_time(self, dashboard_url):
        """Test that dashboard responds quickly."""
        import time
        start = time.time()
        response = requests.get(dashboard_url, timeout=10)
        duration = time.time() - start
        
        assert response.status_code == 200
        # Dashboard should respond in less than 2 seconds
        assert duration < 2.0, f"Dashboard took {duration:.2f}s to respond"

    def test_dashboard_no_authentication_required(self, dashboard_url):
        """Test that dashboard is publicly accessible (no auth required)."""
        # Dashboard should not require API key
        response = requests.get(dashboard_url, timeout=10)
        assert response.status_code == 200
        # Should not get 401 or 403
        assert response.status_code not in [401, 403]


class TestDashboardLinks:
    """Test links and references in the dashboard."""

    def test_dashboard_status_link_format(self, dashboard_url, server_base_url):
        """Test that status API link is properly formatted."""
        response = requests.get(dashboard_url, timeout=10)
        assert response.status_code == 200
        
        html = response.text
        # Should contain a reference to the status endpoint
        # Common patterns: /api/v1/status or href="/api/v1/status"
        assert '/status' in html

    def test_dashboard_health_link_format(self, dashboard_url):
        """Test that health link is properly formatted."""
        response = requests.get(dashboard_url, timeout=10)
        assert response.status_code == 200
        
        html = response.text
        # Should contain reference to health endpoint
        assert '/health' in html


class TestDashboardEdgeCases:
    """Test edge cases and error conditions."""

    def test_dashboard_invalid_method(self, dashboard_url):
        """Test that dashboard only accepts GET requests."""
        # POST should return 405 Method Not Allowed
        response = requests.post(dashboard_url, timeout=10)
        assert response.status_code == 405

    def test_dashboard_head_request(self, dashboard_url):
        """Test that dashboard responds to HEAD requests."""
        response = requests.head(dashboard_url, timeout=10)
        # HEAD should work (200) or return 405
        assert response.status_code in [200, 405]

    def test_dashboard_case_sensitivity(self, server_base_url):
        """Test dashboard URL case sensitivity."""
        # Flask routes are case-sensitive by default
        response = requests.get(f"{server_base_url}/Dashboard", timeout=10)
        # Should get 404 for wrong case
        assert response.status_code == 404

    def test_dashboard_handles_query_parameters(self, dashboard_url):
        """Test that dashboard ignores query parameters."""
        response = requests.get(f"{dashboard_url}?test=123", timeout=10)
        # Should still work, just ignore the parameters
        assert response.status_code == 200


class TestDashboardContent:
    """Test specific content elements in the dashboard."""

    def test_dashboard_has_emoji_indicators(self, dashboard_url):
        """Test that dashboard uses emoji indicators for visual clarity."""
        response = requests.get(dashboard_url, timeout=10)
        assert response.status_code == 200
        
        html = response.text
        # Check for common emojis used in the dashboard
        emojis = ['✅', '📊', '💚', '🚀', '⚠️']
        found_emojis = [emoji for emoji in emojis if emoji in html]
        assert len(found_emojis) > 0, "Dashboard should contain status emojis"

    def test_dashboard_has_proper_structure(self, dashboard_url):
        """Test that dashboard has proper HTML structure."""
        response = requests.get(dashboard_url, timeout=10)
        assert response.status_code == 200
        
        html = response.text.lower()
        # Basic HTML structure checks
        assert '<html' in html
        assert '<head>' in html or '<head ' in html
        assert '<body>' in html or '<body ' in html
        assert '</body>' in html
        assert '</html>' in html

    def test_dashboard_encoding(self, dashboard_url):
        """Test that dashboard uses proper UTF-8 encoding."""
        response = requests.get(dashboard_url, timeout=10)
        assert response.status_code == 200
        
        # Check encoding in headers or content
        assert response.encoding in ['utf-8', 'UTF-8'] or 'utf-8' in response.headers.get('Content-Type', '').lower()
        
        # Should be able to decode emojis without errors
        html = response.text
        assert '✅' in html or 'VPN Sentinel' in html
