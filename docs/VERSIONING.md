# Versioning Strategy

## Overview

VPN Sentinel uses **dynamic semantic versioning** with context-aware version strings that reflect the Git branch and commit state. This provides complete traceability from Docker images back to source code.

## Version Format

```
MAJOR.MINOR.PATCH[-CONTEXT][-COMMIT_HASH]
```

### Components

- **MAJOR**: Breaking changes (increment when incompatible API changes)
- **MINOR**: New features (backward-compatible)
- **PATCH**: Bug fixes (backward-compatible)
- **CONTEXT**: Branch or release stage (dev, main, feature-name)
- **COMMIT_HASH**: Short Git commit hash (7 characters)

## Version Examples

| Context | Version Example | Description | Docker Tags |
|---------|----------------|-------------|-------------|
| **Main (Tagged)** | `1.0.0` | Stable release from tagged commit | `:1.0.0`, `:latest` |
| **Main (Untagged)** | `1.0.0-main-abc1234` | Development on main branch | `:1.0.0-main-abc1234` |
| **Development** | `1.0.0-dev-abc1234` | Active development branch | `:1.0.0-dev-abc1234`, `:development` |
| **Feature Branch** | `1.0.0-feature-auth-abc1234` | Feature branch work | `:1.0.0-feature-auth-abc1234` |
| **Hotfix Branch** | `1.0.1-hotfix-leak-abc1234` | Critical bug fix | `:1.0.1-hotfix-leak-abc1234` |

## Version File

The base version is stored in `VERSION` file at repository root:

```bash
# VERSION file contents
1.0.0
```

**Update manually** when releasing new major/minor versions:

```bash
# Minor version bump
echo "1.1.0" > VERSION
git add VERSION
git commit -m "chore: bump version to 1.1.0"

# Major version bump
echo "2.0.0" > VERSION
git add VERSION
git commit -m "chore: bump version to 2.0.0"
```

## Dynamic Version Generation

The `get_version.sh` script automatically generates context-aware versions:

```bash
#!/bin/bash
# Generates version based on Git context

BASE_VERSION=$(cat VERSION)
BRANCH=$(git rev-parse --abbrev-ref HEAD)
COMMIT_HASH=$(git rev-parse --short HEAD)

# Logic:
# - Main + tag → BASE_VERSION
# - Main + commits → BASE_VERSION-main-HASH
# - Development → BASE_VERSION-dev-HASH
# - Other → BASE_VERSION-BRANCH-HASH
```

### Usage

```bash
# Generate current version
./get_version.sh
# Output: 1.0.0-dev-abc1234

# Use in Docker build
VERSION=$(./get_version.sh)
docker build --build-arg VERSION=$VERSION -t app:$VERSION .

# Check version in running container
docker run --rm app:$VERSION env | grep VERSION
# VERSION=1.0.0-dev-abc1234
```

## Docker Integration

### Build Arguments

Both Dockerfiles accept version as build arguments:

```dockerfile
# Build stage
ARG VERSION=unknown
ARG COMMIT_HASH=unknown

# Runtime stage
ARG VERSION=unknown
ARG COMMIT_HASH=unknown

# Set environment variables
ENV VERSION=${VERSION}
ENV COMMIT_HASH=${COMMIT_HASH}
```

### Build Command

```bash
# Generate version
VERSION=$(./get_version.sh)
COMMIT_HASH=$(git rev-parse --short HEAD)

# Build with version
docker build \
  --build-arg VERSION=$VERSION \
  --build-arg COMMIT_HASH=$COMMIT_HASH \
  -t vpn-sentinel-server:$VERSION \
  -f vpn-sentinel-server/Dockerfile \
  .
```

### OCI Labels

Docker images include standardized OCI labels:

```dockerfile
LABEL org.opencontainers.image.version="1.0.0-dev-abc1234"
LABEL org.opencontainers.image.revision="abc1234567890def"
LABEL org.opencontainers.image.source="https://github.com/agigante80/VPNSentinel"
LABEL org.opencontainers.image.created="2025-12-12T10:30:00Z"
```

Inspect labels:

```bash
docker inspect vpn-sentinel-server:latest | jq '.[0].Config.Labels'
```

## CI/CD Integration

### GitHub Actions Workflow

The CI/CD pipeline automatically:

1. **Generates version** using `get_version.sh`
2. **Passes to Docker builds** via `--build-arg`
3. **Tags images** with generated version
4. **Creates GitHub releases** for main branch tags

```yaml
jobs:
  version:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.version }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Required for git describe
      
      - name: Generate version
        id: version
        run: |
          chmod +x get_version.sh
          VERSION=$(./get_version.sh)
          echo "version=$VERSION" >> $GITHUB_OUTPUT
          echo "Version: $VERSION"
```

### Docker Tag Strategy

| Branch | Condition | Tags |
|--------|-----------|------|
| `main` | Tagged release | `:1.0.0`, `:latest` |
| `main` | Untagged | `:1.0.0-main-abc1234` |
| `development` | Any commit | `:1.0.0-dev-abc1234`, `:development` |
| Feature/hotfix | Any commit | `:1.0.0-branch-abc1234` |

## Release Process

### 1. Development Phase

Work on `development` branch:

```bash
git checkout development
# Make changes
git commit -m "feat: add new monitoring feature"
git push origin development
```

**Result**: Docker images tagged with `:1.0.0-dev-abc1234` and `:development`

### 2. Prepare Release

Update version for release:

```bash
# Update VERSION file
echo "1.1.0" > VERSION
git add VERSION
git commit -m "chore: bump version to 1.1.0"

# Update changelog
# Edit CHANGELOG.md with release notes

git push origin development
```

### 3. Merge to Main

Create PR from `development` to `main`:

```bash
# Create PR via GitHub UI
# After approval and merge:
```

**Result**: Docker images built and tagged with `:1.1.0-main-abc1234`

### 4. Tag Release

Create Git tag for stable release:

```bash
git checkout main
git pull origin main
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin v1.1.0
```

**Result**: 
- Docker images re-tagged with `:1.1.0` and `:latest`
- GitHub Release created automatically
- Docker Hub descriptions updated

## Version Validation

### Pre-commit Checks

Ensure version script is executable:

```bash
# Make executable
chmod +x get_version.sh

# Test generation
./get_version.sh
```

### CI Validation

The CI/CD pipeline validates:

- ✅ `get_version.sh` is executable
- ✅ Version format is valid semver
- ✅ Docker builds succeed with version
- ✅ VERSION env var set in container
- ✅ OCI labels present in image

### Runtime Verification

Check version in running container:

```bash
# Environment variable
docker exec vpn-sentinel-server env | grep VERSION

# Docker inspect
docker inspect vpn-sentinel-server:latest \
  --format='{{.Config.Env}}' | grep VERSION

# Application logs (server displays version at startup)
docker logs vpn-sentinel-server | grep -i version
```

## Semantic Versioning Rules

### Major Version (BREAKING CHANGES)

Increment when making incompatible API changes:

- ❌ Remove API endpoints
- ❌ Change required environment variables
- ❌ Modify API request/response format
- ❌ Change Docker volume paths
- ❌ Break backward compatibility

Example:
```bash
# API key header changed from X-API-Key to Authorization
echo "2.0.0" > VERSION
git commit -m "feat!: change API authentication header

BREAKING CHANGE: API key now uses Authorization header instead of X-API-Key"
```

### Minor Version (NEW FEATURES)

Increment when adding backward-compatible functionality:

- ✅ Add new API endpoints
- ✅ Add optional environment variables
- ✅ Add new Telegram commands
- ✅ Enhance dashboard features
- ✅ Improve logging

Example:
```bash
# Add support for webhooks
echo "1.1.0" > VERSION
git commit -m "feat: add webhook support for notifications"
```

### Patch Version (BUG FIXES)

Increment when making backward-compatible bug fixes:

- 🐛 Fix DNS leak detection logic
- 🐛 Resolve memory leaks
- 🐛 Correct timestamp formatting
- 🐛 Fix dashboard rendering issues

Example:
```bash
# Fix DNS trace parsing
echo "1.0.1" > VERSION
git commit -m "fix: correct DNS trace parsing for Cloudflare format"
```

## Conventional Commits

Use conventional commit format for automatic changelog generation:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Commit Types

| Type | Version Impact | Example |
|------|---------------|---------|
| `feat:` | MINOR | `feat: add Redis caching support` |
| `fix:` | PATCH | `fix: resolve rate limiting bug` |
| `feat!:` or `BREAKING CHANGE:` | MAJOR | `feat!: redesign API authentication` |
| `perf:` | PATCH | `perf: optimize client monitoring loop` |
| `docs:` | None | `docs: update README with new examples` |
| `chore:` | None | `chore: bump dependencies` |
| `test:` | None | `test: add integration test for keepalive` |

### Examples

```bash
# Minor version bump
git commit -m "feat(server): add support for multiple Telegram bots"

# Patch version bump
git commit -m "fix(client): correct IP detection retry logic"

# Major version bump
git commit -m "feat(api)!: change keepalive payload format

BREAKING CHANGE: keepalive endpoint now requires ISO 8601 timestamps"
```

## Troubleshooting

### Version Mismatch

**Problem**: Container shows `VERSION=unknown`

**Solution**:
```bash
# Verify build args passed
docker build --build-arg VERSION=$(./get_version.sh) ...

# Check Dockerfile has ARG/ENV
grep -A2 "ARG VERSION" vpn-sentinel-server/Dockerfile
```

### Git Describe Fails

**Problem**: `get_version.sh` returns `0.0.0-dev-abc1234`

**Solution**:
```bash
# Ensure at least one tag exists
git tag v0.1.0
git push origin v0.1.0

# Verify tags visible
git tag -l
```

### Wrong Branch Detection

**Problem**: `get_version.sh` detects wrong branch name

**Solution**:
```bash
# Check current branch
git rev-parse --abbrev-ref HEAD

# Ensure clean working directory
git status

# Test version generation
./get_version.sh
```

### CI/CD Shallow Clone

**Problem**: GitHub Actions missing tags

**Solution**:
```yaml
# Always use fetch-depth: 0
- uses: actions/checkout@v4
  with:
    fetch-depth: 0  # Required for git describe
```

## Best Practices

### ✅ DO

- **Use `fetch-depth: 0`** in CI/CD for full Git history
- **Make `get_version.sh` executable** before committing
- **Include commit hash** in development builds
- **Update VERSION file** manually for major/minor bumps
- **Tag releases** on main branch for stable versions
- **Use conventional commits** for clear changelog
- **Test version generation** locally before pushing
- **Verify Docker labels** after building images

### ❌ DON'T

- **Don't use `+` in Docker tags** (use `-` instead for build metadata)
- **Don't hardcode versions** in Dockerfile (use ARG/ENV)
- **Don't forget to push tags** after creating them
- **Don't use shallow clones** when version depends on tags
- **Don't mix pre-release and stable** in production
- **Don't skip VERSION file updates** for new major/minor releases

## Future Enhancements

Planned versioning improvements:

- [ ] Automatic VERSION file bump based on commit messages
- [ ] Pre-release tags (alpha, beta, rc)
- [ ] Automated changelog generation from conventional commits
- [ ] Version compatibility checks between client and server
- [ ] Deprecation warnings for old API versions
- [ ] Multi-version Docker image support

---

**Version**: 1.0.0  
**Last Updated**: 2025-12-12  
**Maintainer**: VPN Sentinel Team
