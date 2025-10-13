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
#   keepalive-client:
#     build: ./keepalive-client
#     network_mode: service:gluetun
#     environment:
#       - KEEPALIVE_SERVER_URL=http://your-server:5421
#       - KEEPALIVE_CLIENT_ID=unique-client-name
#       - KEEPALIVE_API_KEY=your-api-key
#
# Environment Variables (configured in docker-compose.yaml):
# - KEEPALIVE_SERVER_URL: URL of the monitoring server (required)
# - KEEPALIVE_CLIENT_ID: Unique identifier for this client
# - KEEPALIVE_API_KEY: Optional API key for server authentication
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
#   docker build -t safeharbor/keepalive-client ./keepalive-client
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
# Package Installation
# -----------------------------------------------------------------------------
# Install curl for HTTP requests to monitoring APIs and server endpoints
# --no-cache: Don't store package index locally to reduce image size
# curl: Essential for communicating with ipinfo.io, Cloudflare, and monitoring server
RUN apk add --no-cache curl \
    && echo "✅ Package installation completed" \
    && echo "📦 Installed packages: curl" \
    && curl --version

# -----------------------------------------------------------------------------
# Script Installation and Configuration
# -----------------------------------------------------------------------------
# Copy the keepalive monitoring script from local directory to container
# The script contains all the VPN monitoring and DNS leak detection logic
COPY keepalive.sh /app/keepalive.sh

# Make the script executable and set proper ownership
# Ensures the script can be executed by the container runtime
RUN chmod +x /app/keepalive.sh \
    && echo "✅ Keepalive script installed and configured" \
    && ls -la /app/keepalive.sh

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
# Alternative approaches:
# 1. External loop: CMD ["sh", "-c", "while true; do /app/keepalive.sh; sleep 300; done"]
# 2. Cron-based: Install crond and use crontab (more complex, less real-time feedback)
# 3. Script-managed: Let keepalive.sh handle its own loop (current approach - recommended)
CMD ["/app/keepalive.sh"]

# -----------------------------------------------------------------------------
# Container Metadata
# -----------------------------------------------------------------------------
# Add labels for better container management and documentation
LABEL maintainer="VPN Sentinel Project" \
      description="VPN Sentinel Client - VPN Monitoring with DNS Leak Detection" \
      version="1.0" \
      license="MIT" \
      purpose="vpn-monitoring" \
      usage="docker run --network=container:your-vpn-container vpn-sentinel/client"

# -----------------------------------------------------------------------------
# Health Check (Optional)
# -----------------------------------------------------------------------------
# Uncomment to add health check that verifies the keepalive process is running
# HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
#   CMD pgrep -f keepalive.sh || exit 1

# =============================================================================
# End of VPN Sentinel Client Dockerfile
# =============================================================================