FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --force --system app \
    && useradd app -g app -d /app

# Copy only the files needed to install dependencies first
COPY --chown=app:app pyproject.toml README.md /app/

# Copy project files
COPY --chown=app:app awslabs/ /app/awslabs/
COPY --chown=app:app docker-healthcheck.sh /usr/local/bin/docker-healthcheck.sh

# Make health check script executable
RUN chmod +x /usr/local/bin/docker-healthcheck.sh \
    && chown -R app:app /app

# Install the package
RUN pip install --no-cache-dir -e .

# Set default environment variables
# Note: SERVER_HOST is intentionally overriding the secure default (127.0.0.1) since containers
# need to bind to all interfaces to be accessible from the host
ENV SERVER_PORT=8888 \
    SERVER_HOST=0.0.0.0

# Expose the default port
EXPOSE 8888

# Switch to non-root user
USER app

# Configure health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD ["docker-healthcheck.sh"]

# Run the server
CMD ["python", "-m", "awslabs.openapi_mcp_server.server"]
