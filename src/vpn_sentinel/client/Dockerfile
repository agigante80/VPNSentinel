# =============================================================================
# VPN Sentinel Client Container
# =============================================================================
#
# This Dockerfile creates a lightweight container for monitoring VPN connectivity
# and detecting DNS leaks. The container is designed to run with network_mode: 
# service:gluetun to share the VPN network stack and test connectivity through
# the VPN tunnel.
#
# Features:
# - Minimal Alpine Linux base for security and size optimization
# - curl for HTTP requests to monitoring APIs and server endpoints
# - Automated keepalive script execution with configurable intervals
# - Real-time VPN status monitoring and DNS leak detection
# - Designed for Docker Compose integration with Gluetun VPN gateway
#
# Usage in Docker Compose:
#   vpn-sentinel-client:
#     build: ./vpn-sentinel-client
#     network_mode: service:gluetun
#     environment:
#       - VPN_SENTINEL_URL=http://your-server:5000
#       - VPN_SENTINEL_API_PATH=/api/v1
#       - VPN_SENTINEL_CLIENT_ID=unique-client-name
#       - VPN_SENTINEL_API_KEY=your-api-key
#
# Environment Variables (configured in docker-compose.yaml):
# - VPN_SENTINEL_URL: Base URL of the monitoring server (required)
# - VPN_SENTINEL_API_PATH: API path prefix (default: /api/v1)
# - VPN_SENTINEL_CLIENT_ID: Unique identifier for this client
# - VPN_SENTINEL_API_KEY: Optional API key for server authentication
# - TZ: Timezone for log timestamps
#
# Network Requirements:
# - Must use network_mode: service:gluetun to route through VPN
# - Requires internet access for API calls (ipinfo.io, cloudflare.com)
# - Needs access to monitoring server endpoint
#
# Security Considerations:
# - Runs as non-root user for security
# - Minimal attack surface with only essential packages
# - No persistent storage or sensitive data in container
# - API key passed via environment variable (not in image)
#
# Build Instructions:
#   docker build -t vpn-sentinel/client ./vpn-sentinel-client
#
# Author: VPN Sentinel Project
# License: MIT
# =============================================================================

# -----------------------------------------------------------------------------
# Base Image Selection
# -----------------------------------------------------------------------------
# Alpine Linux latest - minimal, secure, and frequently updated
# Provides a ~5MB base image with essential utilities and package manager
FROM alpine:latest

# -----------------------------------------------------------------------------
# Build Arguments
# -----------------------------------------------------------------------------
# Accept version information
ARG VERSION
ENV VERSION=${VERSION}
ARG COMMIT_HASH
ENV COMMIT_HASH=${COMMIT_HASH}

# -----------------------------------------------------------------------------
# Package Installation
# -----------------------------------------------------------------------------
# Install curl for HTTP requests to monitoring APIs and server endpoints
# Install python3 and pip for health monitor functionality
# --no-cache: Don't store package index locally to reduce image size
# curl: Essential for communicating with ipinfo.io, Cloudflare, and monitoring server
# python3: Required for Flask-based health monitor
# jq: Required for JSON processing in health monitor
# tzdata: Required for timezone support in Python's zoneinfo module
RUN apk add --no-cache curl python3 py3-pip bash jq tzdata bind-tools \
    && echo "✅ Package installation completed" \
    && echo "📦 Installed packages: curl, python3, py3-pip, bash, jq, tzdata" \
    && curl --version \
    && python3 --version \
    && bash --version \
    && jq --version

# Install Flask for health monitor
# Upgrade pip first to fix CVE-2025-8869
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade 'pip>=25.3' \
    && /opt/venv/bin/pip install --no-cache-dir --retries 10 --timeout 60 flask \
    && echo "✅ Python packages installed: flask"

# Make sure virtual environment is in PATH
ENV PATH="/opt/venv/bin:$PATH"

# -----------------------------------------------------------------------------
# Script Installation and Configuration
# -----------------------------------------------------------------------------
# Copy repository metadata and package sources so pip install works
COPY pyproject.toml /app/pyproject.toml
COPY src/ /app/src/

# Install shared python package so client and server import the same codebase.
# Non-editable install bakes the package into site-packages.
RUN python3 -m pip install --no-cache-dir --retries 10 --timeout 60 /app

# Ensure healthcheck scripts are explicitly copied for container health checks
COPY src/vpn_sentinel/common/health_scripts/healthcheck.py /app/healthcheck.py
COPY src/vpn_sentinel/common/health_scripts/health_monitor_wrapper.py /app/health-monitor.py

# NOTE: the legacy `health_common.py` shim has been migrated to the canonical
# `vpn_sentinel` package and is no longer copied into the image. The
# install (`pip install /app`) installs the canonical package so
# runtime falls back to that implementation instead of the old local shim.

# Make the scripts executable and set proper ownership
# Ensures the scripts can be executed by the container runtime
RUN for f in /app/health-monitor.py /app/healthcheck.py /app/src/vpn_sentinel/common/health_scripts/health_monitor_wrapper.py; do \
            if [ -f "$f" ]; then chmod +x "$f"; fi; \
        done \
        && echo "VPN Sentinel client container built successfully" \
        && ls -la /app/health-monitor.py /app/healthcheck.py || true

# -----------------------------------------------------------------------------
# Working Directory and User Setup
# -----------------------------------------------------------------------------
# Set working directory for better organization and relative path handling
WORKDIR /app

# Create a non-root user for security (optional but recommended)
# Uncomment the lines below to run as non-root user:
# RUN adduser -D -s /bin/sh keepalive
# USER keepalive

# -----------------------------------------------------------------------------
# Container Startup Configuration  
# -----------------------------------------------------------------------------
# Define the default command to execute when container starts
# 
# The script runs continuously with its own interval management (300s/5min default)
# This approach allows the script to handle its own timing, error recovery,
# and provides better logging than external loop management
#
# Multi-process mode: If VPN_SENTINEL_HEALTH_MONITOR=true, both processes run
# Main client: VPN monitoring and keepalive
# Health monitor: Dedicated health status server (port 8082)
#
# Alternative approaches:
# 1. External loop: CMD ["sh", "-c", "while true; do python -m vpn_sentinel.client; sleep 300; done"]
# 2. Cron-based: Install crond and use crontab (more complex, less real-time feedback)
# 3. Script-managed: Let __main__.py handle its own loop (current approach - recommended)
CMD ["python", "-m", "vpn_sentinel.client"]

# -----------------------------------------------------------------------------
# Build-time Configuration
# -----------------------------------------------------------------------------
# Set version from build arguments (passed by CI/CD pipeline)
ARG VERSION
ENV VERSION=${VERSION}

# -----------------------------------------------------------------------------
# Container Metadata
# -----------------------------------------------------------------------------
# Add labels for better container management and documentation
LABEL maintainer="VPN Sentinel Project" \
      description="VPN Sentinel Client - VPN Monitoring with DNS Leak Detection" \
      version="1.0" \
      license="MIT" \
      purpose="vpn-monitoring" \
      usage="docker run --network=container:your-vpn-container vpn-sentinel/client" \
      org.opencontainers.image.title="VPN Sentinel Client" \
      org.opencontainers.image.description="VPN monitoring client that runs inside VPN containers to detect DNS leaks and monitor connection health. Sends status updates to VPN Sentinel Server." \
      org.opencontainers.image.vendor="VPN Sentinel Project" \
      org.opencontainers.image.source="https://github.com/agigante80/VPNSentinel" \
      org.opencontainers.image.licenses="MIT"

# -----------------------------------------------------------------------------
# Health Check Configuration
# -----------------------------------------------------------------------------
# Add comprehensive health check for the VPN Sentinel client
# Verifies process status, server connectivity, external service reachability,
# and optional health monitor status
HEALTHCHECK --interval=60s --timeout=15s --start-period=30s --retries=3 \
    CMD python3 /app/healthcheck.py

# =============================================================================
# End of VPN Sentinel Client Dockerfile
# =============================================================================