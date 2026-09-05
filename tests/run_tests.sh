#!/bin/bash
# shellcheck shell=bash
# Test Runner Script for VPN Sentinel
# Runs comprehensive test suite with proper environment setup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$TEST_DIR")"
COVERAGE_DIR="$TEST_DIR/coverage_html"
COVERAGE_XML="$TEST_DIR/coverage.xml"

echo -e "${BLUE}🧪 VPN Sentinel Test Suite${NC}"
echo "========================================"

# Check dependencies
check_dependencies() {
  echo -e "${YELLOW}📋 Checking dependencies...${NC}"

  if ! command -v python3 &>/dev/null; then
    echo -e "${RED}❌ Python 3 is required but not installed${NC}"
    exit 1
  fi

  if ! command -v pip3 &>/dev/null; then
    echo -e "${RED}❌ pip3 is required but not installed${NC}"
    exit 1
  fi

  echo -e "${GREEN}✅ Dependencies check passed${NC}"
}

# True if running inside an active virtualenv. Used only to make the install-location
# message accurate below; it does not change control flow. --break-system-packages inside
# an active venv still installs into the venv (not system site-packages), so the message
# needs this check to avoid claiming "system packages" when it did not do that.
in_virtualenv() {
  [ -n "${VIRTUAL_ENV:-}" ]
}

# Install the package under test and its test requirements
install_requirements() {
  echo -e "${YELLOW}📦 Installing package and test requirements...${NC}"

  # Install the package under test first (editable install). This step is fatal: if the
  # package itself cannot be installed, nothing downstream (syntax checks that import it,
  # unit tests, coverage) can produce a meaningful result, so a totally broken environment
  # must stop the script here rather than run on and report a false success.
  if pip3 install -e "$PROJECT_ROOT" --quiet --user 2>/dev/null; then
    echo -e "${GREEN}✅ Package installed (editable)${NC}"
  elif pip3 install -e "$PROJECT_ROOT" --quiet --break-system-packages 2>/dev/null; then
    if in_virtualenv; then
      echo -e "${GREEN}✅ Package installed (editable, virtual environment)${NC}"
    else
      echo -e "${GREEN}✅ Package installed (editable, system packages)${NC}"
    fi
  else
    echo -e "${RED}❌ Could not install the package under test${NC}"
    echo -e "${RED}   Consider using: python3 -m venv test_env && source test_env/bin/activate${NC}"
    return 1
  fi

  if [ -f "$TEST_DIR/requirements.txt" ]; then
    # Try to install with pip3, if it fails due to externally managed environment, suggest virtual environment
    if pip3 install -r "$TEST_DIR/requirements.txt" --quiet --user 2>/dev/null; then
      echo -e "${GREEN}✅ Test requirements installed${NC}"
    elif pip3 install -r "$TEST_DIR/requirements.txt" --quiet --break-system-packages 2>/dev/null; then
      if in_virtualenv; then
        echo -e "${GREEN}✅ Test requirements installed (virtual environment)${NC}"
      else
        echo -e "${GREEN}✅ Test requirements installed (system packages)${NC}"
      fi
    else
      # Deliberate warning, not fatal: these are optional dev tools (pytest, coverage,
      # etc). If pytest itself is among what failed to install, that is caught as a fatal
      # "pytest not available" error later in run_unit_tests, so we do not duplicate the
      # fatal exit here.
      echo -e "${YELLOW}⚠️ Could not install test requirements${NC}"
      echo -e "${YELLOW}   Consider using: python3 -m venv test_env && source test_env/bin/activate${NC}"
      echo -e "${YELLOW}   Or run with existing packages...${NC}"
    fi
  else
    # Deliberate warning, not fatal: a missing requirements.txt is unexpected but the
    # required tool it would have installed (pytest) is still checked for, and treated as
    # fatal, in run_unit_tests below.
    echo -e "${YELLOW}⚠️ Test requirements file not found, skipping...${NC}"
  fi
}

# Run syntax checks
run_syntax_checks() {
  echo -e "${YELLOW}🔍 Running syntax checks...${NC}"

  # Check Python syntax
  if python3 -m py_compile "$PROJECT_ROOT/src/vpn_sentinel/server/__main__.py"; then
    echo -e "${GREEN}✅ Server Python syntax OK${NC}"
  else
    echo -e "${RED}❌ Server Python syntax error${NC}"
    return 1
  fi

  # Check Python client syntax
  if python3 -m py_compile "$PROJECT_ROOT/src/vpn_sentinel/client/__main__.py"; then
    echo -e "${GREEN}✅ Client Python script syntax OK${NC}"
  else
    echo -e "${RED}❌ Client Python script syntax error${NC}"
    return 1
  fi

  # Check Docker Compose syntax
  if command -v docker-compose &>/dev/null; then
    compose_files=(
      "$PROJECT_ROOT/compose.yaml"
      "$PROJECT_ROOT/deployments/server-central/compose.yaml"
      "$PROJECT_ROOT/deployments/all-in-one/compose.yaml"
      "$PROJECT_ROOT/deployments/client-with-vpn/compose.yaml"
      "$TEST_DIR/docker-compose.test.yaml"
    )

    for file in "${compose_files[@]}"; do
      if [ -f "$file" ]; then
        if docker-compose -f "$file" config >/dev/null 2>&1; then
          echo -e "${GREEN}✅ $(basename "$file") syntax OK${NC}"
        else
          echo -e "${RED}❌ $(basename "$file") syntax error${NC}"
          return 1
        fi
      fi
    done
  else
    # Deliberate warning, not fatal: docker-compose is optional local tooling for
    # validating compose files. Its absence does not affect Python syntax validity, which
    # is what this function actually gates on.
    echo -e "${YELLOW}⚠️ Docker Compose not available, skipping compose file checks${NC}"
  fi
}

# Run unit tests
run_unit_tests() {
  echo -e "${YELLOW}🧪 Running unit tests...${NC}"

  cd "$TEST_DIR"

  # Both "pytest is missing" and "pytest ran but failed" are fatal here, on purpose. This
  # script used to fall back to "python3 -m unittest discover" in both cases, but unittest
  # does not honour this project's pytest.ini config, markers, or coverage settings, so a
  # silent fallback produced a green run that verified nothing meaningful. There is no
  # legitimate substitute for pytest actually running and passing.
  if ! command -v pytest &>/dev/null; then
    echo -e "${RED}❌ pytest is not available; cannot run the unit test suite${NC}"
    echo -e "${RED}   Install test requirements first (see install_requirements above)${NC}"
    return 1
  fi

  if pytest unit/ -v --tb=short; then
    echo -e "${GREEN}✅ Unit tests completed (using pytest)${NC}"
  else
    echo -e "${RED}❌ Unit tests failed${NC}"
    return 1
  fi
}

# Run integration tests (only if server is running)
run_integration_tests() {
  echo -e "${YELLOW}🔗 Running integration tests...${NC}"

  # Check if server is running. Some deployments expose health on the API path
  # (e.g. http://localhost:5000${API_PATH}/health) while docker-compose test stacks
  # expose a dedicated health server on the HEALTH_PORT (e.g. http://localhost:8081/health).
  # For test environment, check the mapped ports from docker-compose.test.yaml
  API_CHECK_URL="http://localhost:5000${API_PATH}/health"
  HEALTH_CHECK_URL="http://localhost:8081/health"
  TEST_API_CHECK_URL="http://localhost:15553/health"
  TEST_HEALTH_CHECK_URL="http://localhost:15553/health"

  server_up=1
  if curl -sSf "$API_CHECK_URL" >/dev/null 2>&1; then
    server_up=0
  elif curl -sSf "$HEALTH_CHECK_URL" >/dev/null 2>&1; then
    server_up=0
  elif curl -sSf "$TEST_API_CHECK_URL" >/dev/null 2>&1; then
    server_up=0
    # Use test environment URLs
    export VPN_SENTINEL_URL=http://localhost:15554
    export VPN_SENTINEL_API_PATH=/test/v1
  elif curl -sSf "$TEST_HEALTH_CHECK_URL" >/dev/null 2>&1; then
    server_up=0
    # Use test environment URLs
    export VPN_SENTINEL_URL=http://localhost:15554
    export VPN_SENTINEL_API_PATH=/test/v1
  fi

  if [ $server_up -eq 0 ]; then
    echo -e "${GREEN}✅ Server is running, proceeding with integration tests${NC}"

    cd "$TEST_DIR"

    # Set environment variables for integration tests (matching CI/CD workflow)
    export VPN_SENTINEL_URL=http://localhost:5000
    # Use the test API path used by the compose stack (if set in environment), otherwise default to /test/v1
    export VPN_SENTINEL_API_PATH=${VPN_SENTINEL_API_PATH:-/test/v1}
    export VPN_SENTINEL_API_KEY=test-api-key-abcdef123456789

    if command -v pytest &>/dev/null; then
      pytest integration/ -v --tb=short
    else
      python3 -m unittest discover integration/ -v
    fi

    echo -e "${GREEN}✅ Integration tests completed${NC}"
  else
    # Deliberate warning, not fatal: integration tests are opt-in (--integration) and need
    # a live server as a precondition. No server running is an expected local state (the
    # developer just hasn't started the stack), not evidence of a broken environment.
    echo -e "${YELLOW}⚠️ Server not running, skipping integration tests${NC}"
    echo -e "${YELLOW}   Start server with: docker-compose up -d${NC}"
  fi
}

# Generate coverage report
generate_coverage() {
  echo -e "${YELLOW}📊 Generating coverage report...${NC}"

  if command -v pytest &>/dev/null && command -v coverage &>/dev/null; then
    cd "$TEST_DIR"

    # Run tests with coverage.
    # Measure the installed package by module name, matching what CI gates on
    # (--cov=vpn_sentinel.common, 80% floor). The previous "../vpn-sentinel-server"
    # was a path from the pre-src/ layout: it no longer exists, so coverage silently
    # collected nothing and every report here came out empty.
    coverage run --source="vpn_sentinel.common" -m pytest unit/ --quiet

    # Generate reports
    coverage html -d "$COVERAGE_DIR"
    coverage xml -o "$COVERAGE_XML"
    coverage report --show-missing

    echo -e "${GREEN}✅ Coverage report generated${NC}"
    echo -e "${BLUE}📁 HTML report: $COVERAGE_DIR/index.html${NC}"
  else
    # Deliberate warning, not fatal: coverage reporting is optional artifact generation
    # for humans/CI, gated behind --coverage. By the time this runs, run_unit_tests has
    # already required pytest to be present and to pass, so missing coverage tooling here
    # cannot hide a broken test run.
    echo -e "${YELLOW}⚠️ Coverage tools not available, skipping coverage report${NC}"
  fi
}

# Clean up test artifacts
cleanup() {
  echo -e "${YELLOW}🧹 Cleaning up test artifacts...${NC}"

  # Remove Python cache
  find "$TEST_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
  find "$TEST_DIR" -name "*.pyc" -delete 2>/dev/null || true

  echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Main test execution
main() {
  local run_unit=true
  local run_integration=false
  local run_coverage=false
  local cleanup_after=false

  # Parse command line arguments
  while [[ $# -gt 0 ]]; do
    case $1 in
      --integration)
        run_integration=true
        shift
        ;;
      --coverage)
        run_coverage=true
        shift
        ;;
      --cleanup)
        cleanup_after=true
        shift
        ;;
      --all)
        run_integration=true
        run_coverage=true
        cleanup_after=true
        shift
        ;;
      --help)
        echo "Usage: $0 [OPTIONS]"
        echo "Options:"
        echo "  --integration  Run integration tests (requires running server)"
        echo "  --coverage     Generate coverage report"
        echo "  --cleanup      Clean up test artifacts after run"
        echo "  --all          Run all tests with coverage and cleanup"
        echo "  --help         Show this help message"
        exit 0
        ;;
      *)
        echo -e "${RED}❌ Unknown option: $1${NC}"
        exit 1
        ;;
    esac
  done

  # Execute test phases
  check_dependencies
  install_requirements
  run_syntax_checks

  if [ "$run_unit" = true ]; then
    run_unit_tests
  fi

  if [ "$run_integration" = true ]; then
    run_integration_tests
  fi

  if [ "$run_coverage" = true ]; then
    generate_coverage
  fi

  if [ "$cleanup_after" = true ]; then
    cleanup
  fi

  echo -e "${GREEN}🎉 Test suite completed successfully!${NC}"
}

# Handle script interruption
trap 'echo -e "\n${YELLOW}⚠️ Test execution interrupted${NC}"; exit 130' INT

# Run main function with all arguments
main "$@"
