# =============================================================================
# VPN Sentinel Server Container  
# =============================================================================
#
# This Dockerfile creates a Python-based monitoring server that receives
# keepalive messages from VPN clients, performs DNS leak detection, and
# sends real-time notifications via Telegram. The server is designed to
# operate independently from the VPN network to maintain communication
# capabilities even during VPN outages.
#
# Features:
# - Flask web server for REST API endpoints
# - Real-time DNS leak detection and alerting
# - Telegram Bot integration for instant notifications  
# - Rate limiting and IP whitelisting security
# - Client health monitoring with configurable thresholds
# - Interactive Telegram commands (/ping, /status, /help)
# - Comprehensive logging and access monitoring
#
# Network Architecture:
# - Runs on isolated network (NOT through VPN)
# - Accessible from external clients via mapped ports
# - Maintains communication during VPN reconnections
# - Receives data from VPN-routed clients for leak detection
#
# Usage in Docker Compose:
#   keepalive-server:
#     build: ./keepalive-server
#     ports:
#       - "5421:5000"
#     environment:
#       - TELEGRAM_BOT_TOKEN=your_bot_token
#       - TELEGRAM_CHAT_ID=your_chat_id
#       - KEEPALIVE_API_KEY=your_api_key
#     networks:
#       - keepalive-isolated
#
# Environment Variables (configured in docker-compose.yaml):
# - TELEGRAM_BOT_TOKEN: Bot token from @BotFather (required)
# - TELEGRAM_CHAT_ID: Your Telegram chat ID (required)
# - KEEPALIVE_API_KEY: API key for client authentication (optional)
# - ALLOWED_IPS: Comma-separated IP whitelist (optional)
# - MAX_REQUESTS_PER_MINUTE: Rate limiting threshold (default: 30)
# - TZ: Timezone for log timestamps (default: UTC)
#
# Security Considerations:
# - Runs as non-root user for enhanced security
# - Implements rate limiting to prevent abuse
# - Supports IP whitelisting for access control
# - API key authentication for sensitive endpoints
# - Comprehensive request logging for security monitoring
#
# Production Deployment:
# - Use reverse proxy (nginx) for SSL termination
# - Configure proper firewall rules
# - Set up log rotation and monitoring
# - Consider using Redis for client state persistence
# - Monitor resource usage and scale as needed
#
# Build Instructions:
#   docker build -t safeharbor/keepalive-server ./keepalive-server
#
# Author: VPN Sentinel Project
# License: MIT
# =============================================================================

# -----------------------------------------------------------------------------
# Base Image Selection
# -----------------------------------------------------------------------------
# Python 3.11 Alpine - optimal balance of features, security, and size
# Alpine Linux provides a minimal attack surface (~15MB base)
# Python 3.11 offers modern language features and performance improvements
FROM python:3.11-alpine

# -----------------------------------------------------------------------------
# Container Metadata and Documentation
# -----------------------------------------------------------------------------
# Add labels for better container management and documentation
LABEL maintainer="VPN Sentinel Project" \
      description="VPN Sentinel Server - VPN Monitoring & Telegram Notifications" \
      version="1.0.0" \
      license="MIT" \
      python.version="3.11" \
      framework="Flask" \
      purpose="vpn-monitoring" \
      usage="docker run -p 5421:5000 -e TELEGRAM_BOT_TOKEN=xxx vpn-sentinel/server"

# -----------------------------------------------------------------------------
# Working Directory and User Setup
# -----------------------------------------------------------------------------
# Create application directory with proper structure
WORKDIR /app

# Create non-root user for security best practices
# Running as non-root reduces attack surface and follows security guidelines
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup && \
    chown -R appuser:appgroup /app

# -----------------------------------------------------------------------------
# Python Dependencies Installation
# -----------------------------------------------------------------------------
# Install Python packages required for the monitoring server
# Using specific versions for reproducible builds and security
# 
# Dependencies explained:
# - flask: Lightweight web framework for REST API endpoints
# - requests: HTTP client library for Telegram Bot API communication  
# - pytz: Timezone handling for accurate timestamp formatting
#
# Alpine optimizations:
# - Uses pip cache for faster subsequent builds
# - Installs only runtime dependencies (no build tools needed)
RUN pip install --no-cache-dir \
    flask==2.3.3 \
    requests==2.31.0 \
    pytz==2023.3 && \
    echo "✅ Python dependencies installed successfully" && \
    pip list

# Alternative: Using requirements.txt for version pinning
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# Application Code Installation
# -----------------------------------------------------------------------------
# Copy the monitoring server application code
# The server contains all VPN monitoring and notification logic
COPY keepalive-server.py /app/keepalive-server.py

# Set proper file permissions and ownership
RUN chmod +x /app/keepalive-server.py && \
    chown appuser:appgroup /app/keepalive-server.py && \
    echo "✅ Application code installed and configured" && \
    ls -la /app/

# -----------------------------------------------------------------------------
# Network Configuration
# -----------------------------------------------------------------------------
# Expose the Flask application port
# Port 5000 is Flask's default development port
# In production, map this to external port (e.g., 5421:5000)
EXPOSE 5000

# -----------------------------------------------------------------------------
# Runtime Configuration
# -----------------------------------------------------------------------------
# Switch to non-root user for security
USER appuser

# Set Python-specific environment variables for optimal container operation
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_ENV=production \
    FLASK_APP=keepalive-server.py

# -----------------------------------------------------------------------------
# Health Check Configuration
# -----------------------------------------------------------------------------
# Add health check to monitor container status
# Ensures the Flask server is responding to requests
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:5000/health || exit 1

# -----------------------------------------------------------------------------
# Container Startup Configuration
# -----------------------------------------------------------------------------
# Define the command to run when container starts
# 
# Uses Python directly for better process management and signal handling
# The server runs Flask in production mode with proper error handling
# 
# Alternative startup methods:
# 1. Development: CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
# 2. Production: CMD ["gunicorn", "--bind", "0.0.0.0:5000", "keepalive-server:app"]
# 3. Current: Direct Python execution (simple and effective for this use case)
CMD ["python", "keepalive-server.py"]

# -----------------------------------------------------------------------------
# Development and Debugging Notes
# -----------------------------------------------------------------------------
# For development with live reload:
# docker run -v $(pwd)/keepalive-server.py:/app/keepalive-server.py \
#            -p 5421:5000 safeharbor/keepalive-server
#
# For debugging with shell access:
# docker run -it --entrypoint /bin/sh safeharbor/keepalive-server
#
# For production with custom configuration:
# docker run -p 5421:5000 \
#            -e TELEGRAM_BOT_TOKEN=your_token \
#            -e TELEGRAM_CHAT_ID=your_chat_id \
#            -e KEEPALIVE_API_KEY=your_key \
#            safeharbor/keepalive-server

# =============================================================================
# End of VPN Sentinel Server Dockerfile
# =============================================================================