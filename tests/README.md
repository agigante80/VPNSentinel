# VPN Sentinel Testing Documentation

## Overview

This directory contains a comprehensive test suite for the VPN Sentinel project, including unit tests, integration tests, and end-to-end testing capabilities.

## Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── test_server.py      # Server functionality tests  
│   └── test_client.py      # Client functionality tests
├── integration/            # Integration tests
│   └── test_e2e.py        # End-to-end workflow tests
├── fixtures/              # Test data and fixtures
│   └── sample_data.py     # Sample test data
├── utils/                 # Test utilities
│   └── test_helpers.py    # Helper functions and mocks
├── requirements.txt       # Test dependencies
├── .env.test             # Test environment configuration
├── docker-compose.test.yaml # Test Docker environment
└── run_tests.sh          # Test runner script
```

## Running Tests

### Quick Start

1. **Install test dependencies:**
   ```bash
   pip install -r tests/requirements.txt
   ```

2. **Run all tests:**
   ```bash
   ./tests/run_tests.sh --all
   ```

### Individual Test Types

#### Unit Tests Only
```bash
./tests/run_tests.sh
# or
cd tests && python -m pytest unit/ -v
```

#### Integration Tests (requires running server)
```bash
# Start the server first
docker-compose up -d

# Run integration tests
./tests/run_tests.sh --integration
```

#### With Coverage Report
```bash
./tests/run_tests.sh --coverage
```

### Test Runner Options

```bash
./tests/run_tests.sh [OPTIONS]

Options:
  --integration  Run integration tests (requires running server)
  --coverage     Generate coverage report  
  --cleanup      Clean up test artifacts after run
  --all          Run all tests with coverage and cleanup
  --help         Show help message
```

## Test Categories

### Unit Tests (`tests/unit/`)

Test individual components in isolation:

- **Server Tests** (`test_server.py`):
  - API endpoint functionality
  - Telegram command handlers
  - Same-IP detection logic
  - Status determination
  - Dashboard data preparation
  - Server information gathering

- **Client Tests** (`test_client.py`):
  - Shell script syntax validation
  - JSON payload construction
  - API communication logic
  - Error handling and retry logic
  - Data gathering (IP, location, DNS)

### Integration Tests (`tests/integration/`)

Test component interactions:

- **End-to-End Tests** (`test_e2e.py`):
  - Server-client communication
  - API authentication
  - Dashboard accessibility
  - Rate limiting functionality
  - Same-IP warning workflow
  - Configuration validation

### Test Environment

#### Docker Test Environment

Use the isolated test environment:

```bash
# Start test environment
docker-compose -f tests/docker-compose.test.yaml up -d

# Run tests against test environment
cd tests
export VPN_SENTINEL_URL=http://localhost:15554
python -m pytest integration/ -v

# Stop test environment
docker-compose -f tests/docker-compose.test.yaml down -v
```

#### Test Configuration

The test environment uses different ports and configuration:
- **API Port**: 15554 (instead of 5554)
- **Dashboard Port**: 15553 (instead of 5553)
- **API Path**: `/test/v1` (instead of `/api/v1`)
- **Test API Key**: `test-api-key-abcdef123456789`

## Continuous Integration

### GitHub Actions

The project includes a comprehensive CI/CD pipeline (`.github/workflows/ci-cd.yml`):

1. **Syntax & Style Checks**
   - Python syntax validation
   - Shell script syntax validation
   - Docker Compose file validation
   - Code style checking with flake8

2. **Unit Tests**
   - Isolated component testing
   - Test result reporting

3. **Integration Tests**
   - Full Docker environment testing
   - End-to-end workflow validation

4. **Code Coverage**
   - Coverage report generation
   - Upload to Codecov

5. **Security Scanning**
   - Vulnerability scanning with Trivy
   - SARIF report upload

6. **Docker Build Tests**
   - Multi-component Docker image building
   - Container runtime validation

### Local CI Simulation

Run the same checks locally:

```bash
# Syntax checks
python -m py_compile vpn-sentinel-server/vpn-sentinel-server.py
bash -n vpn-sentinel-client/vpn-sentinel-client.sh

# Style checks
flake8 vpn-sentinel-server/ --max-line-length=127

# All tests
./tests/run_tests.sh --all
```

## Test Data and Fixtures

### Sample Data (`tests/fixtures/sample_data.py`)

Provides realistic test data:
- Sample keepalive requests
- Mock server responses  
- Test environment variables
- Expected Telegram messages
- Dashboard template data

### Test Helpers (`tests/utils/test_helpers.py`)

Utility functions for testing:
- Environment variable mocking
- Mock client data generation
- Flask request mocking
- Temporary file handling

## Coverage Reporting

### Generate Coverage Reports

```bash
# Run with coverage
./tests/run_tests.sh --coverage

# View HTML report
open tests/coverage_html/index.html

# View terminal report
coverage report --show-missing
```

### Coverage Targets

- **Target Coverage**: 80%+ overall
- **Critical Components**: 90%+ coverage
  - API endpoints
  - Status logic
  - Same-IP detection
  - Telegram handlers

## Writing New Tests

### Unit Test Example

```python
import unittest
from unittest.mock import patch, Mock

class TestNewFeature(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.test_data = {...}
    
    def test_feature_functionality(self):
        """Test specific feature behavior"""
        # Arrange
        input_data = {...}
        
        # Act
        result = function_under_test(input_data)
        
        # Assert
        self.assertEqual(result, expected_output)
```

### Integration Test Example

```python
import requests
import unittest

class TestNewIntegration(unittest.TestCase):
    def test_api_workflow(self):
        """Test complete API workflow"""
        try:
            # Test API call
            response = requests.get("http://localhost:5554/api/v1/endpoint")
            self.assertEqual(response.status_code, 200)
            
        except requests.ConnectionError:
            self.skipTest("Server not running for integration test")
```

## Debugging Tests

### Verbose Output
```bash
python -m pytest tests/ -v -s
```

### Run Specific Tests
```bash
python -m pytest tests/unit/test_server.py::TestStatusLogic::test_same_ip_detection -v
```

### Debug Integration Issues
```bash
# Check server logs
docker logs vpn-sentinel-server

# Check test environment
docker-compose -f tests/docker-compose.test.yaml logs
```

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Mock External Services**: Don't rely on external APIs in tests
3. **Use Descriptive Names**: Test names should clearly indicate what they test
4. **Test Edge Cases**: Include error conditions and boundary cases
5. **Keep Tests Fast**: Unit tests should run quickly
6. **Use Fixtures**: Reuse common test data and setup
7. **Document Complex Tests**: Add comments for complex test logic

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure test dependencies are installed
2. **Server Not Running**: Integration tests require running server
3. **Port Conflicts**: Test environment uses different ports
4. **Permission Errors**: Ensure test runner script is executable
5. **Docker Issues**: Check Docker daemon and compose version

### Getting Help

- Check test output for specific error messages
- Review logs from Docker containers
- Ensure all environment variables are set correctly
- Verify network connectivity for integration tests