# 📚 VPN Sentinel Documentation

**Comprehensive documentation for VPN Sentinel - Monitor your VPN connections with real-time health checks and instant notifications.**

---

## 🚀 Quick Start

### Installation
```bash
# Clone the repository
git clone https://github.com/agigante80/VPNSentinel.git
cd VPNSentinel

# Build and run with Docker Compose
docker compose up -d
```

### Running Tests
```bash
# Run all tests
./tests/run_tests.sh --all

# Run unit tests only (the default; there is no --unit flag)
./tests/run_tests.sh

# Run integration tests only
./tests/run_tests.sh --integration

# Run with coverage
python3 -m pytest tests/unit/ --cov=vpn_sentinel.common --cov-report=html
```

### Development Commands
```bash
# Lint code
python3 -m flake8 --max-line-length=120 src/

# Build Docker images locally
docker build -t vpn-sentinel-server:latest -f src/vpn_sentinel/server/Dockerfile .
docker build -t vpn-sentinel-client:latest -f src/vpn_sentinel/client/Dockerfile .

# Full local end-to-end check (Docker)
bin/local-env verify
```

---

## 📘 Documentation Index

### Core Documentation
- **[Architecture](./ARCHITECTURE.md)** - System design, components, data flow, and CI/CD pipeline
- **[Versioning Strategy](./VERSIONING.md)** - Semantic versioning, release process, and version management
- **[Testing & Reliability](./TESTING_AND_RELIABILITY.md)** - Testing strategy, frameworks, and CI/CD

### Notifications
- **[Telegram](./TELEGRAM.md)** - Telegram bot setup and commands
- **[Notifications](./NOTIFICATIONS.md)** - Extra alert targets through Apprise

### Decisions and Guides
- **[Architecture Decisions](./architecture/README.md)** - Architecture overview and decision records
- **[Ticket Standards](./guides/ticket-standards.md)** - How tickets are written and gated

### Security
- **[Security & Privacy](./SECURITY_AND_PRIVACY.md)** - Security policies, AI safety, incident response

---

## 🤝 Contribution Policy

### Code Standards
- **Python 3.12+** required
- **PEP 8** compliance (enforced via flake8)
- **Type hints** encouraged for new code
- **Tests required** for all new features
- **Documentation** must be updated with code changes

### Testing Requirements
✅ **All tests must pass before committing**

```bash
# Required before any commit
python3 -m pytest tests/unit/ -q
python3 -m flake8 --max-line-length=120 src/vpn_sentinel/common/
```

### AI-Assisted Development
AI assistants may be used to help maintain this project. Their configuration is kept local to each
contributor and is not part of the repository.

When using AI assistants:
- **Always run tests locally** before committing
- **Update documentation** when code changes
- **Never expose secrets** in code or logs

---

## 📊 Project Structure

```
VPNSentinel/
├── src/vpn_sentinel/
│   ├── server/                # Server application
│   │   ├── __main__.py        # Server entry point
│   │   └── Dockerfile         # Server image
│   ├── client/                # Client application
│   │   ├── __main__.py        # Client entry point
│   │   └── Dockerfile         # Client image
│   └── common/                # Shared library (21 modules)
│   ├── api_routes.py          # API endpoints
│   ├── config.py              # Configuration
│   ├── geolocation.py         # IP geolocation
│   ├── telegram.py            # Telegram integration
│   └── ...                    # 17 more modules
├── tests/                     # Test suite
│   ├── unit/                  # Unit tests (115 passed)
│   ├── integration/           # Integration tests (36 passed)
│   └── run_tests.sh           # Test runner
├── docs/                      # Documentation
├── .github/workflows/         # CI/CD pipelines
└── deployments/               # Deployment examples
```

---

## 🔗 External Resources

- **GitHub Repository**: https://github.com/agigante80/VPNSentinel
- **Docker Hub**: https://hub.docker.com/r/agigante80/vpn-sentinel-server
- **GitHub Container Registry**: ghcr.io/agigante80/vpn-sentinel-server
- **License**: MIT License

---

## 📝 Quick Reference

### Environment Variables
See **[Architecture](./ARCHITECTURE.md)** for complete list

### Notifications
See **[NOTIFICATIONS.md](./NOTIFICATIONS.md)** for extra alert targets (ntfy, Gotify, Discord, email, ...) via Apprise.

### Telegram Setup
See **[Telegram](./TELEGRAM.md)** for setup instructions

### Health Endpoints
- `/health` - Basic health check
- `/health/ready` - Readiness check
- `/health/startup` - Startup check

### API Endpoints
- `POST /api/v1/keepalive` - Client heartbeat
- `GET /api/v1/status` - Client status

---

## 🆘 Support

For issues, questions, or contributions:
1. Check existing **[documentation](./)**
2. Open a GitHub issue with details

---

**Last Updated**: 2026-03-06  
**Version**: 1.1.3  
**Status**: Production Ready
