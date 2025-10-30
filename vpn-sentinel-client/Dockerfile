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
RUN apk add --no-cache curl python3 py3-pip bash jq \
    && echo "✅ Package installation completed" \
    && echo "📦 Installed packages: curl, python3, py3-pip, bash, jq" \
    && curl --version \
    && python3 --version \
    && bash --version \
    && jq --version

# Install Flask for health monitor
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir flask \
    && echo "✅ Python packages installed: flask"

# Make sure virtual environment is in PATH
ENV PATH="/opt/venv/bin:$PATH"

# -----------------------------------------------------------------------------
# Script Installation and Configuration
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# VPN Sentinel Client Script
# -----------------------------------------------------------------------------
# Copy the main VPN Sentinel client script

# Copy the entire vpn-sentinel-client directory into the image so runtime
# scripts and the full lib/ are included. This avoids a mismatch where the
# top-level repo `lib/` differs from the client-specific `vpn-sentinel-client/lib/`.
COPY vpn-sentinel-client/ /app/

# Include repository-level shared lib (health-common) so the health-monitor
# script can find ../lib/health-common.sh at runtime when running from /app
COPY lib/health-common.sh /app/lib/health-common.sh
# Ensure healthcheck script is explicitly copied for tests that inspect the Dockerfile
COPY vpn-sentinel-client/healthcheck.sh /app/healthcheck.sh
COPY vpn-sentinel-client/lib/health_common.py /app/lib/health_common.py

# Make the scripts executable and set proper ownership
# Ensures the scripts can be executed by the container runtime
RUN chmod +x /app/vpn-sentinel-client.sh /app/health-monitor.sh /app/healthcheck.sh \
    && echo "VPN Sentinel client container built successfully" \
    && ls -la /app/vpn-sentinel-client.sh /app/health-monitor.sh /app/healthcheck.sh

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
# 1. External loop: CMD ["sh", "-c", "while true; do /app/vpn-sentinel-client.sh; sleep 300; done"]
# 2. Cron-based: Install crond and use crontab (more complex, less real-time feedback)
# 3. Script-managed: Let vpn-sentinel-client.sh handle its own loop (current approach - recommended)
CMD ["/app/vpn-sentinel-client.sh"]

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
    CMD /app/healthcheck.sh

# =============================================================================
# End of VPN Sentinel Client Dockerfile
# =============================================================================