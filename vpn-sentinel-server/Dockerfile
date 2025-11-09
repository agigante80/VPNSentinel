# VPN Sentinel Server Dockerfile
# Multi-stage build for a lightweight Python server container

# Build stage
FROM python:3.12-alpine AS builder

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev

# Set work directory
WORKDIR /app

# Copy Python project files
COPY pyproject.toml .
COPY vpn_sentinel_common/ ./vpn_sentinel_common/

# Install Python dependencies and Flask
RUN pip install --no-cache-dir --user -e . flask werkzeug

# Runtime stage
FROM python:3.12-alpine

# Install runtime dependencies
RUN apk add --no-cache \
    curl \
    openssl \
    ca-certificates

# Create non-root user
RUN addgroup -g 1001 -S vpnuser && \
    adduser -u 1001 -S vpnuser -G vpnuser

# Set work directory
WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /root/.local /home/vpnuser/.local

# Copy application code
COPY vpn_sentinel_common/ ./vpn_sentinel_common/
COPY vpn-sentinel-server/vpn-sentinel-server.py ./vpn-sentinel-server.py

# Make script executable
RUN chmod +x ./vpn-sentinel-server.py

# Create logs directory
RUN mkdir -p /app/logs && \
    chown -R vpnuser:vpnuser /app

# Switch to non-root user
USER vpnuser

# Set Python path
ENV PATH="/home/vpnuser/.local/bin:$PATH"
ENV PYTHONPATH="/app"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

# Default command - run the server
CMD ["python", "./vpn-sentinel-server.py"]

