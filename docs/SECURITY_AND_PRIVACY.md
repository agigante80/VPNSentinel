# 🔒 Security & Privacy

## Security Principles

VPN Sentinel follows **defense-in-depth** security practices:
- Least privilege access
- Input validation and sanitization
- Secure secret management
- Rate limiting and throttling
- Network isolation
- Minimal attack surface

---

## Authentication & Authorization

### API Key Authentication

**Mechanism**: Shared secret key for API access

**Implementation**:
```python
# vpn_sentinel/common/api_routes.py (authenticate_request)
provided_key = request.headers.get("X-API-Key", "")
if not provided_key:
    return jsonify({"error": "Authentication required", "message": "X-API-Key header is required"}), 401
if not secrets_match(provided_key, API_KEY):
    return jsonify({"error": "Authentication failed", "message": "Invalid API key"}), 403
```

`secrets_match` (`vpn_sentinel/common/config.py`) hashes both values with SHA-256 and compares the
digests with `hmac.compare_digest`, so the comparison takes the same time whatever the length or the
number of matching leading characters. The `/metrics` bearer token uses the same helper. A non-ASCII
key or token is accepted in either its UTF-8 or its latin-1 byte form (the bundled client sends
latin-1, curl and Prometheus send UTF-8); ASCII keys, such as those from the recommended generator,
have exactly one accepted form.

**Security Features**:
- ✅ Constant-time comparison (SHA-256 digests compared with `hmac.compare_digest`; prevents timing attacks)
- ✅ Header-based (not in URL)
- ✅ Configurable via environment variable
- ❌ Single shared key (no per-client keys)

**Best Practices**:
- Use strong random keys (32+ characters)
- Rotate keys periodically
- Store in environment variables, NOT in code
- Use HTTPS in production
- Never log API keys

**Example**:
```bash
# Generate secure API key
openssl rand -base64 32

# Set in environment
export VPN_SENTINEL_API_KEY="your-secure-key-here"
```

---

### IP Whitelisting (Optional)

**Purpose**: Restrict API access to known IPs

**Configuration**:
```bash
VPN_SENTINEL_SERVER_IP_WHITELIST_ENABLED=true
VPN_SENTINEL_ALLOWED_IPS="192.168.1.100,10.0.0.0/8,172.16.0.1"
```

**Use Cases**:
- Internal-only deployments
- Known client IP ranges
- Additional security layer

**Limitations**:
- ❌ Not suitable for dynamic IPs
- ❌ Can block legitimate clients
- ❌ Requires maintenance

---

## Rate Limiting

### Purpose

Protect against:
- DDoS attacks
- Brute force attempts
- Resource exhaustion
- Abusive clients

### Implementation

**Algorithm**: Sliding window

**Configuration**:
```python
VPN_SENTINEL_SERVER_RATE_LIMIT = 30  # requests per minute
```

**Behavior**:
- Tracks requests per IP address
- Returns `429 Too Many Requests` when exceeded
- Automatic cleanup of expired entries
- Health endpoints excluded from limits
- `/metrics` (health app) is public by default and exposes client IDs; set `VPN_SENTINEL_METRICS_TOKEN` (or `_FILE`) to require `Authorization: Bearer <token>` (401 otherwise, constant-time compare, failed attempts logged at most once per 60 s)

**Example Response**:
```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Please wait before retrying.",
  "retry_after": 30
}
```

---

## Input Validation

### Validation Rules

| Field | Validation | Example |
|-------|------------|---------|
| `client_id` | Alphanumeric + hyphens, 1-64 chars | `office-vpn-1` |
| `public_ip` | Valid IPv4/IPv6 | `203.0.113.42` |
| `location` | 2-letter country code | `US` |
| `timestamp` | ISO 8601 format | `2025-01-15T12:34:56Z` |

### Sanitization

**Always sanitize**:
- Client-provided strings
- User inputs from Telegram
- External API responses
- Log messages (prevent log injection)

**Example**:
```python
import re

def sanitize_client_id(client_id):
    """Ensure client_id is safe."""
    if not re.match(r'^[a-zA-Z0-9\-]{1,64}$', client_id):
        raise ValueError("Invalid client_id format")
    return client_id
```

---

## Secret Management

### Environment Variables

**Critical Secrets**:
- `VPN_SENTINEL_API_KEY` - API authentication
- `TELEGRAM_BOT_TOKEN` - Bot token
- `TELEGRAM_CHAT_ID` - Chat identifier
- `IPINFO_API_TOKEN` - Geolocation API token

**Best Practices**:
- ✅ Use environment variables
- ✅ Use Docker secrets for production
- ✅ Never commit secrets to Git
- ✅ Rotate secrets periodically
- ❌ Never hardcode secrets
- ❌ Never log secrets

**Token redaction**: failed Telegram calls raise `requests` errors whose text contains the request URL,
and the bot token is part of that URL (`/bot<TOKEN>/sendMessage`). VPNSentinel replaces the configured
token, and anything shaped like a Telegram bot token, with `[REDACTED]` in the three Telegram error log
lines and again on every line the dashboard `/logs` page shows. Lines already written by older versions
stay in the log file and in `docker logs` history; `/logs` hides them, the files are not rewritten.

**Rotation advice**: rotate the bot token with @BotFather if the server ever logged a Telegram network
error (older versions) AND the logs, the log file, or dashboard port 8080 were reachable by anyone else.
Exposure, not sharing, is the trigger.

### Docker Secrets

Every secret can be supplied from a file with the Docker `_FILE` convention:
`VPN_SENTINEL_API_KEY_FILE`, `TELEGRAM_BOT_TOKEN_FILE` and `TELEGRAM_CHAT_ID_FILE`. The file content,
with all trailing `\r` and `\n` removed, is used as the value. The server and client fail closed:

- Setting both `NAME` and `NAME_FILE` is fatal (the exception is an empty `NAME`, which counts as unset,
  because Compose injects `NAME=` when the host variable is not set).
- A file that is missing, unreadable, a directory, not UTF-8, or empty is fatal. The server exits with code 1
  and the client with code 2, with one `config` log line naming the variable and path (never the content).
  An empty API key is never treated as "authentication disabled".

**Production Setup (plain Compose, file-based secrets)**:
```yaml
services:
  vpn-sentinel-server:
    secrets:
      - vpn_sentinel_api_key
      - telegram_token
    environment:
      - VPN_SENTINEL_API_KEY=
      - VPN_SENTINEL_API_KEY_FILE=/run/secrets/vpn_sentinel_api_key
      - TELEGRAM_BOT_TOKEN=
      - TELEGRAM_BOT_TOKEN_FILE=/run/secrets/telegram_token

secrets:
  vpn_sentinel_api_key:
    file: ./secrets/vpn_sentinel_api_key
  telegram_token:
    file: ./secrets/telegram_token
```

The secret files must be readable by the container user (the server runs as uid 1001), for example mode `0644`
on a directory only you can enter, or `chown` to that uid.

**Swarm variant**: declare the secrets as `external: true` instead of `file:` (created beforehand with
`docker secret create`); the service block is unchanged.

### .env Files

**Development Only**:
```bash
# .env (NEVER commit this file)
VPN_SENTINEL_API_KEY=dev-key-only
TELEGRAM_BOT_TOKEN=123456:ABC-DEF
```

**Add to .gitignore**:
```gitignore
.env
.env.*
!.env.example
```

### Dashboard Pages

Every value shown on `/dashboard` and `/logs` (client fields, server geolocation, version, log text) is
HTML-encoded before it is placed in the page, and the pages are returned as built, never passed through a
template renderer, so log text is displayed literally. The `/logs` line colouring builds DOM nodes with
`textContent`. Dashboard responses send `Content-Security-Policy` (per-request script nonce, no external
sources), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` and `Referrer-Policy: no-referrer`.

---

## Network Security

### Network Isolation

**Client Isolation**: Runs in VPN network namespace

```yaml
vpn-sentinel-client:
  network_mode: service:vpn-client  # Shares VPN network
```

**Benefits**:
- ✅ Client traffic routes through VPN
- ✅ Accurate IP detection
- ✅ DNS leak detection works
- ✅ Cannot bypass VPN

**Security Implications**:
- If VPN compromised, client is exposed
- Client cannot communicate on host network
- Depends on VPN container security

### TLS/HTTPS

**Built-in TLS (server)**: set both `VPN_SENTINEL_TLS_CERT_PATH` and `VPN_SENTINEL_TLS_KEY_PATH` to serve HTTPS on all three listeners. The configuration is validated once at startup and fails closed: if only one variable is set, a file is missing or unreadable, or the pair does not match, the server logs one error naming the variable and exits with code 2. It never falls back to plain HTTP. Exit code 2 means a configuration error; exit code 1 means a listener died at runtime. Note that a shared `.env` which sets only `VPN_SENTINEL_TLS_CERT_PATH` for the client's CA bundle will make the server exit 2. The image HEALTHCHECK uses plain HTTP, so it reports unhealthy when built-in TLS is on.

**Production Recommendation**: Use reverse proxy

**Example (nginx)**:
```nginx
server {
    listen 443 ssl;
    server_name vpn-sentinel.example.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    location /api/v1/ {
        proxy_pass http://localhost:5000;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;
    }
}
```

**Example (Traefik)**:
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.vpn-sentinel.rule=Host(`vpn-sentinel.example.com`)"
  - "traefik.http.routers.vpn-sentinel.tls=true"
  - "traefik.http.routers.vpn-sentinel.tls.certresolver=letsencrypt"
```

---

## Data Privacy

### Data Collection

**What We Collect**:
- Public IP addresses (temporary, in-memory)
- Geolocation data (country, city)
- DNS server location
- VPN connection status
- Timestamps

**What We DON'T Collect**:
- Private IP addresses
- Browsing history
- DNS queries (only leak detection)
- User credentials
- Personal identifiable information (PII)

### Data Storage

**Current Implementation**:
- ✅ In-memory only (no disk persistence)
- ✅ No logging of sensitive data
- ✅ No external data sharing
- ✅ Automatic cleanup on restart

**Privacy Benefits**:
- No long-term data retention
- No data breach risk (ephemeral)
- No user profiling
- GDPR-friendly (minimal data)

### Data Sharing

**Who Has Access**:
- VPN Sentinel server (in-memory)
- Telegram recipients (if enabled)
- Apprise targets (if `VPN_SENTINEL_APPRISE_URLS` is set): any ntfy, Gotify, Discord, email or other service you list
- Dashboard viewers (if enabled)

**Third-Party Services**:
- ipinfo.io / ip-api.com (geolocation)
- Cloudflare (DNS leak detection)
- Telegram Bot API (notifications)
- Your chosen Apprise targets (optional notifications, see [NOTIFICATIONS.md](NOTIFICATIONS.md))

**Mitigation**:
- Use self-hosted geolocation if privacy-critical
- Disable Telegram if not needed
- Leave `VPN_SENTINEL_APPRISE_URLS` unset if you do not want alerts to leave your network

**Apprise targets (optional)**:
- The alerts carry the client ID, the client's VPN public IP, its geolocation and your server's public IP. With Apprise
  configured they are also delivered to every target you list, and that service stores what it receives under your
  own account. VPN Sentinel stores nothing itself. Where the data travels (country, provider) depends on the target you choose.
- A public ntfy topic is readable by anyone who knows or guesses the topic name. Use a long random topic name, or a
  protected topic with credentials, for anything that names your clients and IPs.
- Apprise URLs embed tokens. Treat `VPN_SENTINEL_APPRISE_URLS` as a secret: keep it in a `_FILE` secret or a
  masked field, never in a committed file. VPN Sentinel logs only `scheme://***`.
- Restrict dashboard access

---

## Vulnerability Management

### Security Auditing

**Tools**:
- `bandit` - Python security linter
- `safety` - Dependency vulnerability scanner
- `trivy` - Container image scanner

**Run Security Audit**:
```bash
# Python security scan
pip install bandit
bandit -r src/vpn_sentinel/

# Dependency scan
pip install safety
safety check -r requirements.txt

# Container scan
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image ghcr.io/lcharles0/vpn-sentinel-server:latest
```

### Dependency Updates

**Update Schedule**:
- Critical security patches: Immediate
- High severity: Within 7 days
- Medium severity: Within 30 days
- Low severity: Next release

**Update Process**:
```bash
# Check for updates
pip list --outdated

# Update specific package
pip install --upgrade requests

# Test after update
./tests/run_tests.sh --all
```

### Known Vulnerabilities

**Current Status**: ✅ No known vulnerabilities

**Monitoring**:
- Dependabot alerts enabled
- GitHub Security Advisories monitored
- CVE database checked regularly

---

## Incident Response

### Security Incident Procedure

1. **Detection**: Identify suspicious activity
   - Unusual API patterns
   - Failed authentication attempts
   - Unexpected errors

2. **Containment**: Stop the threat
   - Revoke compromised API keys
   - Block malicious IPs
   - Restart affected services

3. **Investigation**: Understand the breach
   - Review logs
   - Identify entry point
   - Assess damage

4. **Remediation**: Fix the vulnerability
   - Patch code
   - Update dependencies
   - Deploy fix

5. **Communication**: Notify stakeholders
   - Document incident
   - Notify users (if data exposed)
   - Update security docs

6. **Prevention**: Prevent recurrence
   - Add tests for vulnerability
   - Update security policies
   - Improve monitoring

### Reporting Security Issues

**DO NOT create public GitHub issues for security vulnerabilities.**

**Contact**:
- Email: security@example.com
- Encrypted: Use PGP key (see SECURITY.md)
- Response time: 48 hours

**Information to Include**:
- Description of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

---

## Compliance

### GDPR Considerations

**Data Minimization**: ✅ Only collect necessary data

**Purpose Limitation**: ✅ Data used only for VPN monitoring

**Storage Limitation**: ✅ In-memory only (ephemeral)

**Data Portability**: ✅ Users can export via API

**Right to Erasure**: ✅ Restart clears all data

**Security**: ✅ Encrypted transport (HTTPS recommended)

### Container Security

**Best Practices**:
- ✅ Non-root user in containers
- ✅ Minimal base image (Alpine)
- ✅ No unnecessary tools
- ✅ Read-only filesystem where possible
- ✅ Drop unnecessary capabilities

**Example Dockerfile Security**:
```dockerfile
FROM python:3.12-alpine

# Create non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Install dependencies as root
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Switch to non-root user
USER appuser

# Copy application
COPY --chown=appuser:appgroup . /app
WORKDIR /app

CMD ["python", "-m", "vpn_sentinel.server"]
```

---

## AI Agent Security Rules

### Critical Rules for AI Assistants

✅ **MUST**:
- Validate all inputs before processing
- Use environment variables for secrets
- Review security docs before changing auth logic
- Test security features thoroughly
- Document security decisions
- Use least privilege principles

❌ **MUST NOT**:
- Expose secrets in code, logs, or commit messages
- Bypass authentication for convenience
- Disable security features without approval
- Commit secrets to Git (even in tests)
- Trust external input without validation
- Make security changes without testing

### Security Checklist for AI

Before committing code that affects security:

- [ ] No secrets in code or comments
- [ ] Input validation added/updated
- [ ] Authentication not bypassed
- [ ] Rate limiting not disabled
- [ ] Security tests added
- [ ] Docs updated with security notes
- [ ] No new vulnerabilities introduced
- [ ] All tests pass (including security tests)

---

**Security Contact**: security@example.com
