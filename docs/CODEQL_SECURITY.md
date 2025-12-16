# CodeQL Security Scanning

## Overview

VPN Sentinel uses GitHub CodeQL for automated security analysis of Python code. This document explains the configuration, suppressed alerts, and maintenance procedures.

## Current Status

✅ **Production Code**: 0 open security alerts  
⚠️ **Test Code**: 11 suppressed alerts (false positives)  
✅ **Configuration**: `.github/codeql/codeql-config.yml`

### Alert Summary (December 2024)

| Status | Count | Type | Location |
|--------|-------|------|----------|
| ✅ Fixed | 7 | Stack trace exposure, regex issues, workflow permissions | Production code |
| ✅ Dismissed | 2 | pip CVE-2025-8869 | Resolved by pip 25.3 upgrade |
| ⚠️ Suppressed | 11 | URL substring sanitization | Test files only |

## Configuration File

Location: `.github/codeql/codeql-config.yml`

### Key Features

1. **Test File Exclusion**: All files under `tests/**` excluded from certain checks
2. **Query Suites**: Uses `security-extended` and `security-and-quality`
3. **Suppressed Rules**: Two specific rules disabled for test code only

### Suppressed Rules

#### 1. `py/incomplete-url-substring-sanitization` (11 alerts)

**What it detects**: URL validation using substring checks instead of proper parsing

**Example flagged pattern**:
```python
if 'ipinfo.io' in url:
    return mock_response
```

**Why it's flagged**:
- Could match: `https://evil.com/ipinfo.io/malicious`
- Should use: `urlparse(url).netloc == 'ipinfo.io'`

**Why suppressed in tests**:
- ✅ No user input (hardcoded mock URLs)
- ✅ Controlled environment (CI/CD only)
- ✅ Mock responses (no actual HTTP calls)
- ✅ Test assertions (checking correct API called)
- ✅ No security impact (test harness only)

**Affected files**:
- `tests/integration/test_dashboard.py` (1 alert, line 85)
- `tests/unit/test_geolocation.py` (4 alerts, lines 243, 245, 326, 328)
- `tests/unit/test_server_info.py` (6 alerts, lines 36, 38, 118, 122, 226, 230)

**Example from test code**:
```python
# tests/unit/test_server_info.py
@patch('vpn_sentinel_common.server_info.requests.get')
def test_fallback_to_ipify(self, mock_get):
    def mock_responses(url, **kwargs):
        if 'ipinfo.io' in url:      # ← Suppressed by CodeQL config
            raise Exception("ipinfo.io failed")
        elif 'ipify.org' in url:    # ← Suppressed by CodeQL config
            return mock_response
    mock_get.side_effect = mock_responses
```

**Production code comparison**:
```python
# vpn_sentinel_common/server_info.py (production)
def get_server_public_ip():
    try:
        # Uses hardcoded URLs, not substring validation
        response = requests.get('https://ipinfo.io/json', timeout=10)
        return response.json().get('ip', 'Unknown')
    except Exception:
        # Fallback to alternative service
        response = requests.get('https://api.ipify.org?format=json', timeout=10)
        return response.json().get('ip', 'Unknown')
```

#### 2. `py/stack-trace-exposure` (Suppressed in tests)

**What it detects**: Exception stack traces exposed to users

**Why it's flagged**: Information disclosure risk (reveals internal paths, versions)

**Why suppressed in tests**:
- ✅ Tests run in isolated CI/CD
- ✅ Stack traces help debug failures
- ✅ No external users see output
- ✅ Detailed errors speed development

**Production status**: All stack trace exposures fixed (Alerts #1, #2, #6, #20)

## How CodeQL Configuration Works

### 1. Automatic Scanning

GitHub CodeQL runs automatically on:
- Every push to `main` branch
- Every pull request
- Scheduled weekly scans

### 2. Configuration Loading

GitHub loads `.github/codeql/codeql-config.yml` automatically when it exists. No workflow changes needed.

### 3. Alert Filtering

The configuration file uses two methods:

**Method 1: Path Exclusion**
```yaml
paths-ignore:
  - tests/**              # Exclude all test files
  - '**/__pycache__/**'   # Exclude Python cache
```

**Method 2: Query Filters** (More precise)
```yaml
query-filters:
  - exclude:
      id: py/incomplete-url-substring-sanitization
      paths:
        - tests/**
```

## Viewing Security Alerts

### Via GitHub Web Interface

1. Navigate to: https://github.com/agigante80/VPNSentinel/security/code-scanning
2. Filter by:
   - **State**: Open, Fixed, Dismissed
   - **Severity**: Critical, High, Medium, Low, Warning, Note
   - **Tool**: CodeQL, Trivy

### Via GitHub CLI

```bash
# List all alerts
gh api repos/agigante80/VPNSentinel/code-scanning/alerts

# List open alerts only
gh api repos/agigante80/VPNSentinel/code-scanning/alerts \
  --jq '.[] | select(.state == "open")'

# Get specific alert details
gh api repos/agigante80/VPNSentinel/code-scanning/alerts/14

# Count alerts by status
gh api repos/agigante80/VPNSentinel/code-scanning/alerts \
  --jq 'group_by(.state) | map({state: .[0].state, count: length})'
```

### Expected Output (Current)

```json
[
  {"state": "fixed", "count": 7},
  {"state": "dismissed", "count": 2},
  {"state": "open", "count": 0}
]
```

Note: The 11 test file alerts should not appear because they're suppressed by configuration.

## Alert History Timeline

### October 2024: Initial Setup
- **Alert #1-2**: Stack trace exposure in server → ✅ Fixed
- **Alert #3**: Overly permissive regex → ✅ Fixed

### October 29, 2024
- **Alert #4-5**: Missing workflow permissions → ✅ Fixed
- **Alert #6**: Stack trace exposure → ✅ Fixed

### November 10, 2024
- **Alert #7-8**: pip CVE-2025-8869 → ✅ Dismissed (upgraded pip 25.3)

### November 12, 2024
- **Alert #9-19**: URL sanitization in tests → ⚠️ False positives identified

### November 15, 2024
- **Alert #20**: Stack trace in dashboard → ✅ Fixed

### December 16, 2024
- Enhanced CodeQL configuration with comprehensive documentation
- Formalized test file suppression with detailed rationale
- All production alerts resolved, test alerts properly suppressed

## Maintenance Procedures

### When New Alerts Appear

1. **Check Alert Location**
   ```bash
   gh api repos/agigante80/VPNSentinel/code-scanning/alerts/ALERT_NUM \
     --jq '.most_recent_instance.location.path'
   ```

2. **Evaluate Severity**
   - **Production code + High/Critical**: Fix immediately
   - **Production code + Medium/Low**: Fix within sprint
   - **Test code**: Evaluate if suppression appropriate

3. **Fix or Suppress**
   - **Production**: Always fix, never suppress security issues
   - **Test code**: Suppress if false positive, fix if valid concern

### Annual Review Checklist

Perform annually or when major Python version upgrades:

- [ ] Review all suppressed rules - are they still appropriate?
- [ ] Check for new CodeQL rules - do they need test exclusions?
- [ ] Validate production code has zero open alerts
- [ ] Update documentation with any configuration changes
- [ ] Review dismissed alerts - can any be closed permanently?

### Adding New Suppressions

If new false positives appear in test code:

1. **Verify it's actually a false positive**
   - Is it test code or production code?
   - Is the pattern intentional?
   - Is there security risk?

2. **Add to configuration**
   ```yaml
   query-filters:
     - exclude:
         id: py/new-rule-id
         paths:
           - tests/**
   ```

3. **Document the decision**
   - Why suppressed?
   - Example from code
   - Security assessment

4. **Commit with explanation**
   ```bash
   git commit -m "security: suppress py/new-rule-id in test files
   
   Rationale: [explain why it's safe]
   Example: [show code example]
   Assessment: [security impact]"
   ```

## Troubleshooting

### Configuration Not Applied

**Problem**: Alerts still showing after adding to config

**Solution**:
1. Verify file location: `.github/codeql/codeql-config.yml`
2. Check YAML syntax: `yamllint .github/codeql/codeql-config.yml`
3. Wait for next scan (can take 10-15 minutes)
4. Check GitHub Actions logs for CodeQL job

### Too Many False Positives

**Problem**: Excessive alerts in non-critical code

**Solution**:
- Use `paths-ignore` for entire directories
- Use `query-filters` for specific rules
- Consider if the pattern is actually problematic

### Missing Production Alerts

**Problem**: Concerned production code isn't being scanned

**Solution**:
```bash
# Verify production paths NOT in paths-ignore
grep -A 10 "paths-ignore:" .github/codeql/codeql-config.yml

# Should NOT include:
#   - vpn_sentinel_common/**
#   - vpn-sentinel-server/**
#   - vpn-sentinel-client/**
```

## Best Practices

### ✅ DO

- **Review alerts promptly** - Don't let them accumulate
- **Fix production issues** - Never suppress real vulnerabilities
- **Document suppressions** - Explain why each rule is disabled
- **Keep config updated** - Review annually or with Python upgrades
- **Use precise filters** - Prefer `query-filters` over broad `paths-ignore`
- **Test locally first** - Validate fixes before pushing

### ❌ DON'T

- **Suppress production alerts** - Fix the code instead
- **Ignore critical/high severity** - These need immediate attention
- **Over-suppress** - Only disable rules with clear justification
- **Forget documentation** - Future maintainers need context
- **Skip testing** - Ensure fixes don't break functionality

## Integration with CI/CD

### Trivy Security Scanning

VPN Sentinel also uses Trivy for container vulnerability scanning:

```yaml
# .github/workflows/ci-cd.yml
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: vpn-sentinel-${{ matrix.component }}:scan
    format: 'sarif'
    severity: 'CRITICAL,HIGH'
```

**Relationship**: 
- CodeQL: Source code analysis (Python)
- Trivy: Container image vulnerabilities (dependencies, OS packages)

Both tools upload results to GitHub Security tab.

## References

### Official Documentation
- [CodeQL for Python](https://codeql.github.com/docs/codeql-language-guides/codeql-for-python/)
- [Configuring Code Scanning](https://docs.github.com/en/code-security/code-scanning/automatically-scanning-your-code-for-vulnerabilities-and-errors/configuring-code-scanning)
- [CodeQL Query Help](https://codeql.github.com/codeql-query-help/python/)

### VPN Sentinel Resources
- [Security Alerts](https://github.com/agigante80/VPNSentinel/security/code-scanning)
- [CodeQL Config](.github/codeql/codeql-config.yml)
- [CI/CD Workflow](.github/workflows/ci-cd.yml)
- [Security Documentation](./SECURITY_AND_PRIVACY.md)

### Query Rule Documentation
- [py/incomplete-url-substring-sanitization](https://codeql.github.com/codeql-query-help/python/py-incomplete-url-substring-sanitization/)
- [py/stack-trace-exposure](https://codeql.github.com/codeql-query-help/python/py-stack-trace-exposure/)

---

**Document Version**: 1.0.0  
**Last Updated**: 2024-12-16  
**Next Review**: 2025-12-01 (Annual review)  
**Maintainer**: VPN Sentinel Team
