# Python Version Lifecycle

## Overview

This document provides guidance on Python version selection for VPN Sentinel, based on the official Python release cycle and production best practices.

## Python Release Cycle (PEP 602)

Since Python 3.9, Python follows an **annual release cycle** with predictable support phases:

- **12 months**: Release cycle (new minor version every October)
- **2 years**: Bugfix phase (bug fixes + security fixes, binaries released ~every 2 months)
- **3 years**: Security phase (security fixes only, source-only releases)
- **5 years total**: End-of-life

## Release Phases

### 1. Feature (Pre-Beta)
- **Duration**: ~18 months before release
- **Accepts**: New features, bug fixes, security fixes
- **Status**: Main branch development

### 2. Prerelease (Beta/RC)
- **Duration**: 4-6 months before release
- **Accepts**: Feature fixes, bug fixes, security fixes
- **Status**: Beta and release candidate testing

### 3. Bugfix (Active Maintenance)
- **Duration**: 2 years after release
- **Accepts**: Bug fixes and security fixes
- **Releases**: New binaries ~every 2 months
- **Status**: Production-ready, fully supported

### 4. Security (Security-Only)
- **Duration**: 3 years after bugfix phase ends
- **Accepts**: Security fixes only
- **Releases**: Source-only as needed
- **Status**: Maintenance mode, no new features or bug fixes

### 5. End-of-Life
- **Duration**: After 5 years total
- **Accepts**: Nothing, branch frozen
- **Status**: No longer supported

## Current Python Version Status (December 2024)

### Supported Versions

| Version | Status | Released | EOL | Release Manager |
|---------|--------|----------|-----|-----------------|
| **3.15** | feature | 2026-10-01 | 2031-10 | Hugo van Kemenade |
| **3.14** | bugfix | 2025-10-07 | 2030-10 | Hugo van Kemenade |
| **3.13** | bugfix | 2024-10-07 | 2029-10 | Thomas Wouters |
| **3.12** | security | 2023-10-02 | 2028-10 | Thomas Wouters |
| **3.11** | security | 2022-10-24 | 2027-10 | Pablo Galindo Salgado |
| **3.10** | security | 2021-10-04 | 2026-10 | Pablo Galindo Salgado |

### Unsupported Versions

| Version | Status | Released | EOL | Notes |
|---------|--------|----------|-----|-------|
| **3.9** | end-of-life | 2020-10-05 | 2025-10-31 | Last 1.5yr bugfix cycle |
| **3.8** | end-of-life | 2019-10-14 | 2024-10-07 | - |
| **3.7** | end-of-life | 2018-06-27 | 2023-06-27 | - |
| **3.6** | end-of-life | 2016-12-23 | 2021-12-23 | - |

## VPN Sentinel Python Version Policy

### Current Version: Python 3.12

**Rationale**:
- Released October 2023 (15+ months of production hardening)
- Currently in **security phase** (October 2025 - October 2028)
- Proven stable in production environments
- Full ecosystem support (Docker images, dependencies, tooling)
- Conservative stability-first approach

### Why Not Python 3.13?

**Python 3.13 Status** (as of December 2024):
- Released: October 7, 2024 (3 months ago)
- Phase: Bugfix (early active maintenance)
- EOL: October 2029

**Decision**: Reject Python 3.13 for now

**Reasons**:
1. **Maturity**: Only 3 months old, still in early bugfix phase
2. **Ecosystem**: Docker ecosystem, dependencies, and tooling need time to stabilize
3. **Production Risk**: Too new for production use, potential undiscovered issues
4. **No Urgency**: Both 3.12 and 3.13 in active support, no security pressure
5. **Conservative Pattern**: Consistent with project's stability-first approach

### Python Version Upgrade Timeline

| Timeframe | Action | Criteria |
|-----------|--------|----------|
| **Q1-Q2 2025** | Monitor 3.13 adoption | Track production deployments, ecosystem maturity |
| **Q3-Q4 2025** | Evaluate upgrade | After 1 year of 3.13 stability, assess benefits |
| **2026+** | Consider upgrade | 3.13 proven stable, 3.12 approaching security-only phase |

### Dependabot Configuration

VPN Sentinel uses Dependabot to ignore unstable Python versions:

```yaml
# .github/dependabot.yml
- package-ecosystem: "docker"
  directory: "/vpn-sentinel-server"
  ignore:
    - dependency-name: "python"
      versions: ["3.13", "3.14", "3.15", "3.16", "3.17", "3.18"]
      update-types: ["version-update:semver-major", "version-update:semver-minor"]
```

**Rationale**: Stay on Python 3.12 LTS until 3.13 is proven stable in production environments.

## Python Version Selection Guidelines

### ✅ DO Use Python Version When:

- Released at least **12 months ago** (full year of production hardening)
- In **bugfix phase** with regular maintenance releases
- Widely adopted in production environments
- Full ecosystem support (Docker official images, major dependencies)
- No known critical issues or regressions

### ❌ DON'T Use Python Version When:

- Released less than **6 months ago** (too new, insufficient testing)
- In **prerelease phase** (alpha, beta, RC)
- In **security-only phase** with newer alternatives available
- In **end-of-life status**
- Major ecosystem dependencies not yet compatible

### Security Considerations

**When to upgrade immediately**:
- Current version entering **end-of-life**
- Critical security vulnerability in current version with no backport
- Security-only phase ending within 6 months

**When to defer upgrade**:
- Current version in **bugfix phase** with active support
- New version too recent (< 6 months old)
- No security urgency
- Stability more important than latest features

## Docker Base Image Strategy

### Current Configuration

```dockerfile
# Build stage
FROM python:3.12-alpine AS builder

# Runtime stage
FROM python:3.12-alpine
```

### Version Pinning Strategy

**DO**:
- Pin to **minor version** (e.g., `python:3.12-alpine`)
- Use official Docker Python images
- Test new versions in development branch first
- Update after version proven stable (6-12 months)

**DON'T**:
- Use `latest` tag (unpredictable, breaks reproducibility)
- Use `3-alpine` (too broad, unexpected major upgrades)
- Skip testing before production deployment
- Rush to newest version without evaluation

## Python Version Compatibility Matrix

| Python Version | Alpine Linux | pip Version | Status | Production Ready |
|----------------|--------------|-------------|--------|------------------|
| **3.13** | 3.19+ | 24.2+ | Bugfix | ⚠️ Too new (wait 6-12 months) |
| **3.12** | 3.18+ | 23.2+ | Security | ✅ **Recommended** |
| **3.11** | 3.16+ | 22.3+ | Security | ✅ Stable, consider 3.12 |
| **3.10** | 3.14+ | 21.3+ | Security | ⚠️ Aging, upgrade to 3.12 |
| **3.9** | 3.13+ | 20.3+ | EOL Oct 2025 | ❌ End-of-life soon |

## Decision Framework

When evaluating a Python version upgrade, consider:

### 1. Release Age
- **< 3 months**: Too new, skip
- **3-6 months**: Monitor, evaluate
- **6-12 months**: Consider upgrade
- **12+ months**: Safe to upgrade

### 2. Support Phase
- **Feature**: Never use in production
- **Prerelease**: Never use in production
- **Bugfix**: Ideal for new projects after 6+ months
- **Security**: Acceptable if mature (12+ months)
- **EOL**: Immediate upgrade required

### 3. Ecosystem Maturity
- Official Docker images available
- Major dependencies compatible
- Production deployments successful
- No critical bug reports
- Community adoption widespread

### 4. Project Requirements
- Breaking changes acceptable?
- New features needed?
- Security vulnerabilities in current version?
- Maintenance effort justified?
- Testing resources available?

## Historical Python Version Decisions

### v1.1.2 (December 2024): Rejected Python 3.13

**Context**:
- Dependabot PR #60 proposed Python 3.12 → 3.13
- Python 3.13 released October 7, 2024 (3 months prior)
- All CI checks passing

**Decision**: Closed PR, configured Dependabot to ignore 3.13

**Rationale**:
- Only 3 months old, insufficient production validation
- Python 3.12 in active security phase (until October 2028)
- No security urgency to upgrade
- Conservative stability approach
- Ecosystem needs time to mature

**Outcome**:
- Remained on Python 3.12-alpine
- Updated `.github/dependabot.yml` to ignore 3.13-3.18
- Documented decision in PR #60 comments
- Set review timeline for Q3-Q4 2025

## References

### Official Documentation
- [PEP 602: Annual Release Cycle for Python](https://peps.python.org/pep-0602/)
- [Python Developer's Guide: Development Cycle](https://devguide.python.org/developer-workflow/development-cycle/)
- [Python Developer's Guide: Status of Python Versions](https://devguide.python.org/versions/)
- [Python Release Schedule](https://www.python.org/downloads/)

### Version Tracking
- [Python Release Status](https://devguide.python.org/versions/)
- [Python End of Life Tracker](https://endoflife.date/python)
- [Python Version History](https://python3.info/about/versions.html)

### Docker Images
- [Official Python Docker Images](https://hub.docker.com/_/python)
- [Python Alpine Image Tags](https://hub.docker.com/_/python?tab=tags&page=1&name=alpine)

## Best Practices Summary

### ✅ DO

- **Wait 6-12 months** after release before upgrading to new Python version
- **Stay on LTS versions** (bugfix phase, 12+ months old)
- **Monitor EOL dates** and plan upgrades 6 months in advance
- **Test thoroughly** in development before production deployment
- **Document decisions** in PR comments and this document
- **Configure Dependabot** to ignore unstable versions
- **Follow release cycle** and official Python recommendations

### ❌ DON'T

- **Rush to newest version** without evaluation period
- **Use alpha/beta/RC** in production
- **Ignore EOL warnings** (upgrade before end-of-life)
- **Skip testing** on version upgrades
- **Use `latest` tag** in Dockerfiles
- **Upgrade without reviewing** breaking changes and migration guides

---

**Document Version**: 1.0.0  
**Last Updated**: 2024-12-16  
**Next Review**: 2025-06-01 (Q2 2025 - Python 3.13 evaluation)  
**Maintainer**: VPN Sentinel Team
