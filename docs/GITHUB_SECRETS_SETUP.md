# GitHub Secrets Setup Guide

## Required Secrets for CI/CD Pipeline

The CI/CD workflow requires Docker Hub credentials to publish images. Follow these steps to configure the secrets:

## 1. Generate Docker Hub Access Token

1. Log in to [Docker Hub](https://hub.docker.com/)
2. Click on your username (top right) → **Account Settings**
3. Navigate to **Security** → **Personal access tokens** (or **New Access Token**)
4. Click **Generate New Token**
5. Token settings:
   - **Description**: `GitHub Actions - VPNSentinel`
   - **Access permissions**: **Read, Write, Delete** (for publishing images)
6. Click **Generate**
7. **Copy the token immediately** (it won't be shown again)

## 2. Add Secrets to GitHub Repository

1. Go to your GitHub repository: https://github.com/agigante80/VPNSentinel
2. Click **Settings** tab
3. In left sidebar: **Secrets and variables** → **Actions**
4. Click **New repository secret** button

### Add DOCKER_USERNAME

- **Name**: `DOCKER_USERNAME`
- **Value**: Your Docker Hub username (e.g., `agigante80`)
- Click **Add secret**

### Add DOCKER_TOKEN

- **Name**: `DOCKER_TOKEN`
- **Value**: Paste the access token you copied earlier
- Click **Add secret**

## 3. Verify Secrets Configuration

After adding both secrets, you should see:

```
Repository secrets:
- DOCKER_USERNAME
- DOCKER_TOKEN
```

**Note**: `GITHUB_TOKEN` is automatically provided by GitHub Actions and doesn't need to be added.

## 4. Re-run Failed Workflow

1. Go to **Actions** tab in GitHub
2. Find the failed workflow run
3. Click **Re-run failed jobs** button

The workflow should now successfully authenticate to Docker Hub and publish images.

## Security Best Practices

✅ **DO**:
- Use Docker Hub access tokens (not your password)
- Set appropriate token permissions (read/write only)
- Rotate tokens periodically (every 90 days)
- Revoke unused tokens immediately
- Use descriptive token names for tracking

❌ **DON'T**:
- Never commit tokens to Git
- Don't use your Docker Hub password
- Don't share tokens across projects
- Don't give tokens more permissions than needed

## Troubleshooting

### "Username and password required" Error

**Cause**: Secrets not configured or misspelled

**Solution**:
```bash
# Check if secrets exist (won't show values, only names)
gh secret list

# Expected output:
# DOCKER_TOKEN     Updated YYYY-MM-DD
# DOCKER_USERNAME  Updated YYYY-MM-DD
```

### "Invalid username or password" Error

**Cause**: Token expired or incorrect credentials

**Solution**:
1. Generate new Docker Hub token
2. Update `DOCKER_TOKEN` secret in GitHub
3. Re-run workflow

### "denied: requested access to the resource is denied" Error

**Cause**: Token doesn't have write permissions or username mismatch

**Solution**:
1. Verify Docker Hub repository exists: `agigante80/vpn-sentinel-server`
2. Check token has **Write** permissions
3. Ensure `DOCKER_USERNAME` matches repository owner

## Alternative: GHCR Only (No Docker Hub)

If you prefer to publish only to GitHub Container Registry (GHCR), you can:

1. Remove Docker Hub login step from workflow
2. Remove Docker Hub publishing from tags
3. Use only GHCR tags: `ghcr.io/${{ github.repository_owner }}/vpn-sentinel-{server,client}`

GHCR authentication uses `GITHUB_TOKEN` automatically (no secrets needed).

## Verification

After secrets are configured, the workflow will:

✅ Authenticate to Docker Hub  
✅ Authenticate to GHCR  
✅ Build multi-platform images (amd64 + arm64)  
✅ Push to both registries with version tags  
✅ Update Docker Hub descriptions (main branch only)  

Check successful run output:
```
Log in to Docker Hub
  ✓ Authenticated as agigante80
Log in to GitHub Container Registry
  ✓ Authenticated as agigante80
Build and push server
  ✓ Pushed agigante80/vpn-sentinel-server:0.1.0-dev-abc1234
  ✓ Pushed ghcr.io/agigante80/vpn-sentinel-server:0.1.0-dev-abc1234
```

---

**Last Updated**: 2025-12-12  
**Workflow Version**: 1.0.0
