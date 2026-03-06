# 🧪 Testing & Reliability

## Testing Philosophy

> **Every feature must be tested. Every test must pass before merging.**

VPN Sentinel follows a **test-first reliability approach**:
- Comprehensive unit tests for all logic
- Integration tests for API endpoints
- Smoke tests for Docker deployments
- Pre-commit hooks enforce quality
- CI/CD validates all changes

---

## Test Framework

### Technology Stack

- **Framework**: pytest 7.4.0+
- **Coverage**: pytest-cov
- **Mocking**: unittest.mock
- **HTTP Testing**: Flask test client
- **Linting**: flake8

### Test Structure

```
tests/
├── unit/                     # Unit tests (fast, isolated)
│   ├── test_api_routes.py    # API keepalive/status endpoints (13 tests)
│   ├── test_config.py        # Configuration loading (34 tests)
│   ├── test_dashboard_routes.py  # Dashboard rendering (13 tests)
│   ├── test_geolocation.py   # Geolocation APIs (21 tests)
│   ├── test_health_monitor.py # Health monitor (8 tests)
│   ├── test_health_routes.py # Health check endpoints (4 tests)
│   ├── test_monitor.py       # Monitor heartbeats (6 tests)
│   ├── test_network.py       # Network utilities (23 tests)
│   ├── test_payload.py       # Client payload building (17 tests)
│   ├── test_security.py      # Rate limiting & IP whitelist (15 tests)
│   ├── test_server_info.py   # Server IP detection (14 tests)
│   ├── test_server_utils.py  # Server utilities (14 tests)
│   ├── test_utils.py         # Utility functions (21 tests)
│   ├── test_validation.py    # Input validation (35 tests)
│   ├── test_version.py       # Version management (21 tests)
│   ├── test_server.py        # Server logic tests
│   ├── test_client.py        # Client logic tests
│   ├── test_common_logging.py
│   └── test_common_network_edgecases.py
│
├── integration/              # Integration tests (slower, real services)
│   ├── test_api_path.py      # API path configuration
│   ├── test_client_keepalive_client_id.py
│   ├── test_client_monitor_endpoints.py
│   ├── test_dashboard.py     # Dashboard functionality
│   └── test_rate_limiting.py
│
├── fixtures/                 # Test data and helpers
│   ├── sample_data.py        # Mock responses
│   └── test_server.py       # Mock server for testing
│
├── conftest.py               # Pytest configuration
├── pytest.ini                # Pytest settings
├── requirements.txt          # Test dependencies
└── run_tests.sh              # Test runner script
```

---

## Test Categories

### 1. Unit Tests (291 tests)

**Purpose**: Test individual functions and classes in isolation

**Characteristics**:
- ⚡ Fast execution (<1 second per test)
- 🔒 No external dependencies
- 🎭 Use mocks for external APIs
- ✅ High coverage (90%+ achieved on 16/19 modules)

**Example Test**:
```python
def test_parse_dns_trace_cloudflare_format():
    """Test parsing Cloudflare's quoted format."""
    trace = 'fl="195f311" loc=US colo=SJC'
    result = parse_dns_trace(trace)
    assert result['loc'] == 'US'
    assert result['colo'] == 'SJC'
```

**Run Command**:
```bash
python3 -m pytest tests/unit/ -v
```

---

### 2. Integration Tests (36 tests)

**Purpose**: Test component interactions and API contracts

**Characteristics**:
- 🐢 Slower execution (1-5 seconds per test)
- 🌐 Requires test server instances
- 🔗 Tests cross-component communication
- ✅ Validates real HTTP requests

**Example Test**:
```python
def test_keepalive_endpoint(test_server_url):
    """Test keepalive endpoint accepts valid data."""
    response = requests.post(
        f"{test_server_url}/api/v1/keepalive",
        json={
            "client_id": "test-client",
            "public_ip": "1.2.3.4",
            "location": "US"
        },
        headers={"X-API-Key": "test-key"}
    )
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'
```

**Run Command**:
```bash
python3 -m pytest tests/integration/ -v
```

---

### 3. Smoke Tests

**Purpose**: Validate Docker builds and deployments

**Characteristics**:
- 🐳 Tests actual container images
- 🚀 Validates deployment patterns
- 🔍 Checks service connectivity
- ⏱️ Quick validation (<2 minutes)

**Run Command**:
```bash
bash scripts/smoke/run_local_smoke.sh
```

**What It Tests**:
- Docker images build successfully
- Containers start without errors
- Health endpoints respond
- API accepts authenticated requests
- Client can reach server

---

## Test Execution

### Quick Test (Local Development)

```bash
# Run unit tests only (fast)
python3 -m pytest tests/unit/ -q

# Run with coverage
python3 -m pytest tests/unit/ --cov=vpn_sentinel_common --cov-report=html

# Run specific test file
python3 -m pytest tests/unit/test_server.py -v

# Run specific test function
python3 -m pytest tests/unit/test_server.py::test_keepalive_endpoint -v
```

### Full Test Suite

```bash
# Run all tests (unit + integration)
./tests/run_tests.sh --all

# Run unit tests only
./tests/run_tests.sh --unit

# Run integration tests only
./tests/run_tests.sh --integration

# Run with coverage report
./tests/run_tests.sh --all --coverage
```

### CI/CD Tests

```bash
# Same commands as CI uses
python3 -m pytest tests/unit/ -q
python3 -m flake8 --max-line-length=120 vpn_sentinel_common/
```

---

## Test Coverage

### Current Coverage

Generate a live coverage report to see current numbers:

### View Coverage Report

```bash
# Generate HTML coverage report
python3 -m pytest tests/unit/ --cov=vpn_sentinel_common --cov-report=html

# Open in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

---

## Testing Policies

### Pre-Commit Requirements

✅ **Must Pass Before Commit**:
- All unit tests pass
- Linting passes (flake8)
- No new uncovered lines
- Test files exist for new code

❌ **Blocked Commits**:
- Failing tests
- Linting errors
- Uncovered critical code paths
- Missing docstrings for public functions

### Pre-Merge Requirements

✅ **Must Pass Before Merge to `main`**:
- All unit tests pass (115/115)
- All integration tests pass (36/36)
- Smoke tests pass
- Coverage maintained or improved
- Documentation updated
- CHANGELOG.md updated

### Automated Enforcement

**Pre-commit Hooks** (`.git/hooks/pre-commit`):
```bash
#!/bin/bash
# Run unit tests
python3 -m pytest tests/unit/ -q || exit 1

# Run linting
python3 -m flake8 --max-line-length=120 vpn_sentinel_common/ || exit 1

echo "✅ All pre-commit checks passed"
```

**Install Hooks**:
```bash
bash scripts/setup/install-hooks.sh
```

---

## Writing Tests

### Unit Test Template

```python
import pytest
from vpn_sentinel_common.logging import log_info

def test_log_info_formats_correctly():
    """Test that log_info formats messages with component prefix."""
    # Arrange
    component = "api"
    message = "Test message"
    
    # Act
    result = log_info(component, message)
    
    # Assert
    assert component in result
    assert message in result
```

### Integration Test Template

```python
import pytest
import requests

def test_keepalive_endpoint_integration(test_server_url, api_key):
    """Test keepalive endpoint with real server."""
    # Arrange
    payload = {
        "client_id": "test-client",
        "public_ip": "1.2.3.4",
        "location": "US"
    }
    headers = {"X-API-Key": api_key}
    
    # Act
    response = requests.post(
        f"{test_server_url}/api/v1/keepalive",
        json=payload,
        headers=headers
    )
    
    # Assert
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'
```

### Mock External APIs

```python
from unittest.mock import patch, Mock

@patch('requests.get')
def test_get_location_with_mock(mock_get):
    """Test geolocation with mocked API response."""
    # Arrange
    mock_response = Mock()
    mock_response.json.return_value = {
        "country": "US",
        "city": "San Francisco"
    }
    mock_response.status_code = 200
    mock_get.return_value = mock_response
    
    # Act
    result = get_location("1.2.3.4")
    
    # Assert
    assert result['country'] == 'US'
    assert result['city'] == 'San Francisco'
```

---

## Test Fixtures

### Common Fixtures (conftest.py)

```python
import pytest
from flask import Flask

@pytest.fixture
def test_app():
    """Create a test Flask app."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def test_client(test_app):
    """Create a test client."""
    return test_app.test_client()

@pytest.fixture
def api_key():
    """Provide test API key."""
    return "test-api-key-12345"

@pytest.fixture
def test_server_url():
    """Provide test server URL."""
    return "http://localhost:15000"
```

---

## Debugging Failed Tests

### View Detailed Output

```bash
# Show full output
python3 -m pytest tests/unit/test_server.py -v -s

# Show local variables on failure
python3 -m pytest tests/unit/test_server.py --showlocals

# Stop on first failure
python3 -m pytest tests/unit/ -x

# Re-run only failed tests
python3 -m pytest tests/unit/ --lf
```

### Debug with pdb

```python
def test_complex_logic():
    """Test complex logic with debugging."""
    import pdb; pdb.set_trace()  # Set breakpoint
    
    result = complex_function()
    assert result == expected
```

### Common Test Failures

| Error | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError` | Missing dependency | `pip install -r tests/requirements.txt` |
| `Connection refused` | Server not running | Start test server or use mocks |
| `AssertionError` | Logic error | Check expected vs actual values |
| `Timeout` | Slow external API | Use mocks for external calls |
| `ImportError` | Wrong Python path | Run from project root |

---

## CI/CD Testing

### GitHub Actions Workflow

```yaml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r tests/requirements.txt
      - name: Run unit tests
        run: python3 -m pytest tests/unit/ -v
      - name: Run linting
        run: python3 -m flake8 --max-line-length=120 vpn_sentinel_common/

  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Start test server
        run: docker compose -f tests/docker-compose.test.yaml up -d
      - name: Run integration tests
        run: python3 -m pytest tests/integration/ -v
      - name: Stop test server
        run: docker compose -f tests/docker-compose.test.yaml down
```

**Current CI Status**: ✅ All pipelines passing

---

## Reliability Metrics

### Test Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Unit Tests | 115 passed | 100+ | ✅ |
| Integration Tests | 36 passed | 30+ | ✅ |
| Code Coverage | 78% | 75% | ✅ |
| Test Execution Time | <30s | <60s | ✅ |
| Flake8 Violations | 0 | 0 | ✅ |

### Deployment Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Build Success Rate | 100% | >95% | ✅ |
| Docker Image Size | 80MB | <100MB | ✅ |
| Startup Time | <5s | <10s | ✅ |
| Health Check Success | 100% | >99% | ✅ |

### Monitoring Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| API Uptime | 99.9% | >99% | ✅ |
| Average Response Time | 50ms | <100ms | ✅ |
| Keepalive Success Rate | 99.5% | >99% | ✅ |
| Telegram Delivery | 98% | >95% | ✅ |

---

## Test Maintenance

### Adding New Tests

**When to add tests**:
- Adding new features
- Fixing bugs (add regression test)
- Refactoring code
- Changing API contracts
- Adding dependencies

**Test checklist**: add a unit test for the new function, an integration test for any new endpoint, tests for error conditions and edge cases, updated fixtures if needed, and a docstring explaining the test's purpose.

### Updating Existing Tests

**When to update tests**:
- API contract changes
- Behavior changes
- Mock data becomes outdated
- External API changes
- Test flakiness detected

**Update checklist**: review affected tests, update assertions and mocks, verify all tests still pass, and document changes in the test docstring.


