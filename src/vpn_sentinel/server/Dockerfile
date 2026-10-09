# VPN Sentinel Server Dockerfile
# Multi-stage build for a lightweight Python server container

# Build stage
FROM python:3.12-alpine AS builder

# Build arguments for version information
ARG VERSION
ARG COMMIT_HASH

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev

# Set work directory
WORKDIR /app

# Copy Python project files
COPY pyproject.toml .
COPY src/ ./src/

# Install Python dependencies and Flask with retry logic
# Upgrade the build-time pip first. This does not reach the shipped image: the runtime
# stage below upgrades its own pip for CVE-2025-8869.
RUN pip install --no-cache-dir --upgrade 'pip>=26.2.1' && \
    pip install --no-cache-dir --user --retries 10 --timeout 60 . 'flask>=3.1.3' 'werkzeug>=3.1.9'

# Runtime stage
FROM python:3.12-alpine

# Build arguments for version information
ARG VERSION
ARG COMMIT_HASH

# Set version environment variables
ENV VERSION=${VERSION}
ENV COMMIT_HASH=${COMMIT_HASH}

# Install runtime dependencies
# Note: curl removed as it's not available in Alpine 3.23+ (libcurl is in base image)
RUN apk add --no-cache \
    tzdata \
    ca-certificates

# Upgrade pip in the stage that ships (CVE-2025-8869, fixed in pip 25.3). The builder
# stage's upgrade does not carry over: only /root/.local is copied, so without this the
# image keeps whatever pip the base image bundles (25.0.1 when this was added, #119).
RUN pip install --no-cache-dir --upgrade 'pip>=26.2.1'

# Create non-root user
RUN addgroup -g 1001 -S vpnuser && \
    adduser -u 1001 -S vpnuser -G vpnuser

# Set work directory
WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /root/.local /home/vpnuser/.local

# Create logs directory
RUN mkdir -p /app/logs && \
    chown -R vpnuser:vpnuser /app

# Switch to non-root user
USER vpnuser

# Set Python path
ENV PATH="/home/vpnuser/.local/bin:$PATH"

# Health check (using wget since curl is not available in Alpine 3.23+)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD sh -c 'health_port=${VPN_SENTINEL_SERVER_HEALTH_PORT:-8081}; wget -q -O - http://127.0.0.1:$health_port/health || exit 1'

# Default command - run the server
CMD ["python", "-m", "vpn_sentinel.server"]

