FROM python:3.11-slim

WORKDIR /app

# Install UV for faster package management
RUN pip install uv

# Copy requirements first for better caching
COPY pyproject.toml ./
COPY uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY awslabs/ ./awslabs/
COPY tests/ ./tests/

# Health check script
COPY docker-healthcheck.sh ./
RUN chmod +x docker-healthcheck.sh

# Expose the default MCP port
EXPOSE 3000

# Set environment variables
ENV PYTHONPATH=/app
ENV AWS_DEFAULT_REGION=us-east-1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["./docker-healthcheck.sh"]

# Run the MCP server
CMD ["uv", "run", "python", "-m", "awslabs.cloudwan_mcp_server"]