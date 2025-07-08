# Use Python 3.10 slim image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy project files
COPY . .

# Install dependencies
RUN uv sync --frozen

# Create a non-root user
RUN useradd -m -u 1000 mcpuser && chown -R mcpuser:mcpuser /app
USER mcpuser

# Health check script
COPY docker-healthcheck.sh /app/docker-healthcheck.sh
RUN chmod +x /app/docker-healthcheck.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /app/docker-healthcheck.sh

# Set the entrypoint
ENTRYPOINT ["uv", "run", "awslabs.healthlake-mcp-server"]
