# 🤖 AI Interaction Guide

## Purpose

This document defines **clear operational boundaries** for AI agents assisting with VPN Sentinel development. It ensures safe, consistent, and high-quality AI-assisted contributions.

---

## ⚠️ Critical Rule: Local Testing Enforcement

### **🚫 BLOCKING REQUIREMENT**

✅ **The AI must ALWAYS run the complete test suite locally before committing or pushing to GitHub.**

**Commits and pushes are BLOCKED if any tests fail.**

### Required Commands

```bash
# 1. Run all unit tests
python3 -m pytest tests/unit/ -q

# 2. Run linting
python3 -m flake8 --max-line-length=120 vpn_sentinel_common/ vpn-sentinel-server/ vpn-sentinel-client/

# 3. Run integration tests (if applicable)
python3 -m pytest tests/integration/ -q

# 4. Run smoke tests (if Docker changes)
bash scripts/smoke/run_local_smoke.sh
```

### Enforcement Process

1. **Before any code change**: Verify current tests pass
2. **After code changes**: Run full test suite
3. **If tests fail**: Fix issues, do NOT commit
4. **If tests pass**: Proceed with commit and push
5. **Document results**: Note test outcomes in commit message

---

## 🛡️ Safe Modification Rules

### Security-First Principles

1. **Review Security Policies First**
   - Read `SECURITY_AND_PRIVACY.md` before editing sensitive logic
   - Never modify authentication without security review
   - Validate all input data before processing

2. **Path and Input Validation**
   - Validate file paths before writing
   - Sanitize user inputs
   - Use allowlists for expected values
   - Never trust external data

3. **Secret Management**
   - Never expose secrets, credentials, or PII in logs or code
   - Use environment variables for sensitive data
   - Never commit `.env` files with real credentials
   - Redact sensitive data in examples

4. **Least Privilege**
   - Make minimal necessary changes
   - Avoid broad refactors without approval
   - Document why each change is needed
   - Respect existing architecture patterns

---

## 📝 Documentation Sync Policy

### **Automatic Documentation Updates**

> After every code modification, the AI must identify affected docs and update them.

### Update Mapping

| Code Change | Required Documentation Updates |
|------------|-------------------------------|
| Add new API route | `ARCHITECTURE.md` (API section) |
| Modify test suite | `TESTING_AND_RELIABILITY.md` |
| Complete refactor task | `REFACTORING_PLAN.md` (check off item) |
| Change auth logic | `SECURITY_AND_PRIVACY.md` |
| Add environment variable | `ARCHITECTURE.md` (Environment Variables) |
| Add new dependency | `PROJECT_OVERVIEW.md` (Tech Stack) |
| Fix security issue | `SECURITY_AND_PRIVACY.md`, `IMPROVEMENT_AREAS.md` |
| Add new feature | `PROJECT_OVERVIEW.md`, `ROADMAP.md` |

### Documentation Quality Standards

- **Concise**: No unnecessary verbosity
- **Actionable**: Include commands, examples, and procedures
- **Up-to-date**: Reflect current codebase state
- **Consistent**: Follow existing formatting and structure
- **Complete**: Cover all aspects of the change

---

## 🔧 Common Development Commands

### Building

```bash
# Build server image
docker build -t vpn-sentinel-server:local -f vpn-sentinel-server/Dockerfile .

# Build client image
docker build -t vpn-sentinel-client:local -f vpn-sentinel-client/Dockerfile .

# Build both with Docker Compose
docker compose build
```

### Testing

```bash
# Run all tests
./tests/run_tests.sh --all

# Run unit tests only
./tests/run_tests.sh --unit

# Run integration tests only
./tests/run_tests.sh --integration

# Run specific test file
python3 -m pytest tests/unit/test_server.py -v

# Run with coverage
python3 -m pytest tests/unit/ --cov=vpn_sentinel_common --cov-report=html
```

### Linting

```bash
# Lint Python code
python3 -m flake8 --max-line-length=120 vpn_sentinel_common/

# Check specific file
python3 -m flake8 vpn-sentinel-server/vpn-sentinel-server.py

# Auto-fix with autopep8 (if available)
autopep8 --in-place --aggressive --aggressive <file>
```

### Running

```bash
# Start all services
docker compose up -d

# Start with logs
docker compose up

# Stop all services
docker compose down

# Rebuild and start
docker compose up -d --build

# View logs
docker compose logs -f vpn-sentinel-server
docker compose logs -f vpn-sentinel-client
```

---

## 💡 Example AI Workflows

### Workflow 1: Adding a New API Endpoint

**Prompt**: "Add a new endpoint to handle user registration"

**AI Process**:
1. ✅ Read current `api_routes.py` to understand patterns
2. ✅ Read `SECURITY_AND_PRIVACY.md` for auth requirements
3. ✅ Add new route to `vpn_sentinel_common/api_routes.py`
4. ✅ Add validation logic
5. ✅ Write unit tests in `tests/unit/test_server.py`
6. ✅ Run tests: `python3 -m pytest tests/unit/ -q`
7. ✅ Update `ARCHITECTURE.md` (API Endpoints section)
8. ✅ Run linting: `flake8 vpn_sentinel_common/api_routes.py`
9. ✅ Commit with message: "feat: Add user registration endpoint\n\nAdded POST /api/v1/register endpoint with validation.\nUpdated ARCHITECTURE.md with new endpoint.\nAll tests passing (115/115)."
10. ✅ Push to develop branch

### Workflow 2: Refactoring Email Service

**Prompt**: "Refactor the email service into separate modules"

**AI Process**:
1. ✅ Check `REFACTORING_PLAN.md` for existing refactor tasks
2. ✅ Read current email service code
3. ✅ Create new module structure in `vpn_sentinel_common/`
4. ✅ Migrate functions to new modules
5. ✅ Update imports in dependent files
6. ✅ Write unit tests for new modules
7. ✅ Run full test suite: `./tests/run_tests.sh --all`
8. ✅ Update `ARCHITECTURE.md` (Module Structure)
9. ✅ Update `REFACTORING_PLAN.md` (check off task)
10. ✅ Commit and push
11. ✅ Document in `IMPROVEMENT_AREAS.md` if any issues found

### Workflow 3: Adding Unit Tests

**Prompt**: "Write unit tests for the new payment processor"

**AI Process**:
1. ✅ Read payment processor code to understand functionality
2. ✅ Create test file: `tests/unit/test_payment.py`
3. ✅ Write tests for:
   - Happy path scenarios
   - Edge cases
   - Error handling
   - Input validation
4. ✅ Use mocks for external API calls
5. ✅ Run tests: `python3 -m pytest tests/unit/test_payment.py -v`
6. ✅ Achieve >80% coverage
7. ✅ Update `TESTING_AND_RELIABILITY.md` (Test Coverage section)
8. ✅ Commit with test results in message
9. ✅ Push to develop branch

### Workflow 4: Security Vulnerability Fix

**Prompt**: "Fix SQL injection vulnerability in user query"

**AI Process**:
1. ✅ Read `SECURITY_AND_PRIVACY.md` for security standards
2. ✅ Identify vulnerable code
3. ✅ Implement parameterized queries
4. ✅ Add input validation
5. ✅ Write security-focused unit tests
6. ✅ Run all tests: `./tests/run_tests.sh --all`
7. ✅ Run security audit: `bandit -r vpn_sentinel_common/`
8. ✅ Update `SECURITY_AND_PRIVACY.md` (Document fix)
9. ✅ Update `IMPROVEMENT_AREAS.md` (Remove from debt list)
10. ✅ Commit with security note: "security: Fix SQL injection in user query"
11. ✅ Create security advisory if needed

---

## 🚨 What AI Must NOT Do

### Prohibited Actions

❌ **Never**:
- Commit or push code with failing tests
- Expose secrets or credentials in code, logs, or documentation
- Send private data to external services
- Make breaking changes without approval
- Delete files without understanding dependencies
- Modify security logic without thorough review
- Skip documentation updates
- Ignore linting errors
- Bypass test requirements
- Commit directly to `main` branch (use `develop`)

### High-Risk Operations

⚠️ **Require Extra Caution**:
- Authentication and authorization changes
- Database schema modifications
- API contract changes
- Security-related code
- Dockerfile modifications
- CI/CD pipeline changes
- Dependency updates
- Configuration file changes

**For high-risk operations**:
1. Announce intent before making changes
2. Review existing patterns thoroughly
3. Run comprehensive tests
4. Document all changes extensively
5. Request human review if uncertain

---

## ✅ AI Quality Checklist

Before committing, verify:

- [ ] All tests pass locally
- [ ] Linting passes without errors
- [ ] Documentation updated for changes
- [ ] No secrets or credentials in code
- [ ] Input validation added where needed
- [ ] Error handling is robust
- [ ] Changes follow existing patterns
- [ ] Tests cover new functionality
- [ ] Commit message is descriptive
- [ ] Changes are minimal and focused

---

## 🔄 Continuous Improvement

### Learning from Changes

After each significant change:
1. Review test results
2. Check for new patterns or improvements
3. Update documentation with lessons learned
4. Add to `IMPROVEMENT_AREAS.md` if issues found
5. Suggest better approaches for future

### Feedback Loop

- Monitor test failures and patterns
- Track documentation gaps
- Identify repetitive manual steps
- Propose automation opportunities
- Report unclear requirements

---

## 📚 Reference Documentation

Always consult these before major changes:

1. **[SECURITY_AND_PRIVACY.md](./SECURITY_AND_PRIVACY.md)** - Security rules
2. **[ARCHITECTURE.md](./ARCHITECTURE.md)** - System design
3. **[TESTING_AND_RELIABILITY.md](./TESTING_AND_RELIABILITY.md)** - Test requirements
4. **[REFACTORING_PLAN.md](./REFACTORING_PLAN.md)** - Ongoing work
5. **[IMPROVEMENT_AREAS.md](./IMPROVEMENT_AREAS.md)** - Known issues

---

## 🆘 When to Ask for Human Help

Request human review when:
- Security implications are unclear
- Breaking changes are necessary
- Tests fail for unknown reasons
- Documentation contradicts code
- Architectural decisions needed
- Multiple approaches seem valid
- Uncertainty about requirements
- Fixing introduces new issues

---

**Last Updated**: 2025-11-11  
**Enforcement**: Mandatory for all AI-assisted development  
**Violations**: Will be caught in pre-commit hooks and CI
