# VPN Sentinel - AI Coding Assistant Instructions

## Architecture Overview

VPN Sentinel uses a **distributed client-server architecture** with network isolation:
- **VPN Sentinel Client**: Runs inside VPN container network, monitors connectivity
- **VPN Sentinel Server**: Runs on host network, receives monitoring data and sends notifications
- **Multi-app Flask server**: API (port 5000), Health (port 8081), Dashboard (port 8080)

## Critical Development Rules

### Path Usage
**NEVER use absolute paths referring to `/home/$USER`** - Use relative paths or environment variables for portability across different development environments.

### Security & Privacy
**NEVER include values from `.env` files or private configuration** - All examples should use placeholder values or environment variable references. Private information must never be committed.

### Requirement Conflicts
**If a new requirement contradicts these copilot-instructions, ASK FOR CONFIRMATION before implementing** - These instructions establish the project's architectural patterns, security standards, and development workflows. Changes to these patterns should be intentional and approved.

### Pre-Push Requirements
**ALWAYS build local server and client containers before pushing** unless explicitly specified otherwise:
```bash
# Build server
docker build -t vpn-sentinel-server:latest vpn-sentinel-server/

# Build client  
docker build -t vpn-sentinel-client:latest vpn-sentinel-client/

# Verify builds work
docker run --rm vpn-sentinel-server:latest --help
docker run --rm vpn-sentinel-client:latest --help
```

### Pre-Merge Requirements
**ALWAYS run ALL tests before merging to main branch** unless explicitly specified otherwise:
```bash
# Run complete test suite
./tests/run_tests.sh --all

# Ensure no test failures or regressions
```

### Testing Requirements
**ALWAYS add/review test cases after implementing new functionality**:
- Unit tests for new functions/classes
- Integration tests for new endpoints/features
- Update existing tests if behavior changes
- Test error conditions and edge cases

## Key Design Patterns

### Environment-Driven Configuration
All configuration uses environment variables with sensible defaults:
```python
API_PORT = int(os.getenv("VPN_SENTINEL_SERVER_API_PORT", "5000"))
HEALTH_PORT = int(os.getenv("VPN_SENTINEL_SERVER_HEALTH_PORT", "8081"))
API_KEY = os.getenv("VPN_SENTINEL_API_KEY", "")
```

### Structured Logging with Component Prefixes
Use component-based logging for easy filtering:
```python
log_info("api", f"🌐 Access: {endpoint} | IP: {ip} | Auth: {auth_info}")
log_warn("security", f"⚠️ VPN BYPASS WARNING: Client {client_id} has same IP as server")
log_error("telegram", f"❌ Failed to send message: HTTP {response.status_code}")
```

### Security Middleware Pattern
Apply security checks before all API routes:
```python
@api_app.before_request
def before_request():
    if request.path == '/dashboard' and WEB_DASHBOARD_ENABLED:
        return None  # Public endpoint
    security_result = security_middleware()
    if security_result:
        return security_result
```

### Threading for Background Services
Use daemon threads for monitoring and polling:
```python
checker_thread = threading.Thread(target=check_clients, daemon=True)
checker_thread.start()
```

### Docker Network Mode Sharing
Client containers share VPN network namespace:
```yaml
vpn-sentinel-client:
  network_mode: service:vpn-client  # Shares VPN network stack
```

## Development Workflow

### Local Testing Commands
```bash
# Run full test suite
./tests/run_tests.sh --all

# Run specific test categories
./tests/run_tests.sh --unit
./tests/run_tests.sh --integration

# Start development stack
docker compose up -d

# Debug with logs
docker compose logs -f vpn-sentinel-server
```

### Environment Setup for Testing
Tests require specific environment variables:
```bash
VPN_SENTINEL_API_PATH=/api/v1
VPN_SENTINEL_SERVER_API_PORT=5000
VPN_SENTINEL_SERVER_HEALTH_PORT=8081
FLASK_ENV=testing
```

### Health Check Integration
All components include Docker health checks:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8081/health || exit 1
```

## Code Organization

### Server Structure (`vpn-sentinel-server/`)
- `vpn-sentinel-server.py`: Main server with Flask apps, monitoring, Telegram integration
- Multi-app architecture: `api_app`, `health_app`, `dashboard_app`
- Background threads: client monitoring, Telegram polling

### Client Structure (`vpn-sentinel-client/`)
- `vpn-sentinel-client.sh`: Bash script for monitoring and API calls
- `healthcheck.sh`: Docker health check script
- Network-aware: runs in VPN container's network namespace

### Test Structure (`tests/`)
- `unit/`: Component testing with mocks
- `integration/`: End-to-end testing with real servers
- `fixtures/`: Test data and sample requests
- `run_tests.sh`: Comprehensive test runner with coverage

## Common Patterns

### API Response Format
Standard JSON responses with status and metadata:
```python
return jsonify({
    'status': 'ok',
    'message': 'Keepalive received',
    'server_time': get_current_time().isoformat()
})
```

### Error Handling with Fallbacks
Graceful degradation with "Unknown" defaults:
```python
def get_server_public_ip():
    try:
        response = requests.get('https://ipinfo.io/json', timeout=10)
        return response.json().get('ip', 'Unknown')
    except Exception:
        return 'Unknown'
```

### Client Identification
Use kebab-case identifiers for clients:
```bash
VPN_SENTINEL_CLIENT_ID=office-vpn-primary
VPN_SENTINEL_CLIENT_ID=synology-vpn-media
```

### Telegram Message Formatting
Use HTML formatting with emojis and structured layout:
```python
message = f"✅ <b>VPN Connected!</b>\\n\\n"
message += f"Client: <code>{client_id}</code>\\n"
message += f"VPN IP: <code>{public_ip}</code>\\n"
```

## Deployment Patterns

### Network Isolation
- Client runs in VPN network namespace for accurate monitoring
- Server runs on host network for external accessibility
- Use `network_mode: service:vpn-client` for network sharing

### Port Mapping
- API: 5000 (authenticated endpoints)
- Health: 8081 (public health checks)
- Dashboard: 8080 (web interface)

### Environment Inheritance
Child containers inherit environment from parent services automatically.

## Security Considerations

### Authentication
- API key required for sensitive endpoints
- Health endpoints are public (no auth required)
- IP whitelisting available for additional security

### Input Validation
- Sanitize all client-provided data
- Validate IP addresses, client IDs, location strings
- Use allowlists for expected values

### Rate Limiting
- Sliding window rate limiting per IP
- Configurable limits (default: 30 requests/minute)
- Automatic cleanup of expired entries

## Testing Guidelines

### Unit Tests
- Mock external APIs (ipinfo.io, Telegram)
- Test error conditions and edge cases
- Use fixtures for consistent test data

### Integration Tests
- Start real server instances for testing
- Test actual HTTP endpoints and responses
- Verify cross-component communication

### Test Environment Variables
Always set test-specific environment variables to avoid conflicts with production settings.