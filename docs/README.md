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

# Run unit tests only
./tests/run_tests.sh --unit

# Run integration tests only
./tests/run_tests.sh --integration

# Run with coverage
python3 -m pytest tests/unit/ --cov=vpn_sentinel_common --cov-report=html
```

### Development Commands
```bash
# Lint code
python3 -m flake8 vpn-sentinel-server/ vpn-sentinel-client/ vpn_sentinel_common/

# Build Docker images locally
docker build -t vpn-sentinel-server:latest -f vpn-sentinel-server/Dockerfile .
docker build -t vpn-sentinel-client:latest -f vpn-sentinel-client/Dockerfile .

# Run smoke tests
bash scripts/smoke/run_local_smoke.sh
```

---

## 📘 Documentation Index

### Core Documentation
- **[Project Overview](./PROJECT_OVERVIEW.md)** - Purpose, goals, features, and technology stack
- **[Architecture](./ARCHITECTURE.md)** - System design, components, data flow, and CI/CD pipeline
- **[Versioning Strategy](./VERSIONING.md)** - Semantic versioning, release process, and version management
- **[Testing & Reliability](./TESTING_AND_RELIABILITY.md)** - Testing strategy, frameworks, and CI/CD

### Development Guides
- **[AI Interaction Guide](./AI_INTERACTION_GUIDE.md)** - Rules for AI-assisted development, local testing enforcement
- **[Refactoring Plan](./REFACTORING_PLAN.md)** - Ongoing improvements and completed tasks
- **[Improvement Areas](./IMPROVEMENT_AREAS.md)** - Known technical debt and recommendations

### Security & Planning
- **[Security & Privacy](./SECURITY_AND_PRIVACY.md)** - Security policies, AI safety, incident response
- **[Roadmap](./ROADMAP.md)** - Future improvements and priority timeline

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
python3 -m flake8 --max-line-length=120 vpn_sentinel_common/
```

### AI-Assisted Development
When using AI assistants (GitHub Copilot, ChatGPT, etc.):
- Follow the **[AI Interaction Guide](./AI_INTERACTION_GUIDE.md)**
- **Always run tests locally** before committing
- **Update documentation** when code changes
- **Never expose secrets** in code or logs

---

## 📊 Project Structure

```
VPNSentinel/
├── vpn-sentinel-server/       # Server application
│   ├── vpn-sentinel-server.py # Entry point
│   └── Dockerfile             # Server image
├── vpn-sentinel-client/       # Client application
│   ├── vpn-sentinel-client.py # Pure Python client
│   └── Dockerfile             # Client image
├── vpn_sentinel_common/       # Shared library (21 modules)
│   ├── api_routes.py          # API endpoints
│   ├── config.py              # Configuration
│   ├── geolocation.py         # IP geolocation
│   ├── telegram.py            # Telegram integration
│   └── ...                    # 17 more modules
├── tests/                     # Test suite (249 tests)
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

### Telegram Setup
See **[Architecture](./ARCHITECTURE.md#telegram-integration)** for setup instructions

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
2. Review **[Improvement Areas](./IMPROVEMENT_AREAS.md)**
3. Open a GitHub issue with details

---

**Last Updated**: 2025-11-11  
**Version**: 1.0.0-dev  
**Status**: Production Ready
