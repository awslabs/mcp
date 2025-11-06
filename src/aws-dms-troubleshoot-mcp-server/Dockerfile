FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY awslabs ./awslabs
COPY docker-healthcheck.sh ./

# Make healthcheck script executable
RUN chmod +x docker-healthcheck.sh

# Install uv for faster dependency management
RUN pip install --no-cache-dir uv

# Install the package and its dependencies
RUN uv pip install --system --no-cache .

# Create application user and set ownership
RUN groupadd -r app && \
    useradd -r -g app -d /app -s /sbin/nologin app && \
    chown -R app:app /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FASTMCP_LOG_LEVEL=INFO

# Switch to non-root user
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["/app/docker-healthcheck.sh"]

# Run the server
ENTRYPOINT ["python", "-m", "awslabs.aws_dms_troubleshoot_mcp_server.server"]
