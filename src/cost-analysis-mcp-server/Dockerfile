FROM python:3.12-slim

WORKDIR /awslabs/cost_analysis_mcp_server

# install astral uv for Python dependencies
RUN pip install uv

# Copy project files
COPY pyproject.toml .
COPY server.py .

# Install dependencies using uv
RUN uv pip install --no-cache --system -e .

# Add AWS configuration directory
RUN mkdir -p /root/.aws

# Expose port for SSE transport
EXPOSE 8000

# Run the MCP server
CMD ["python", "server.py"]