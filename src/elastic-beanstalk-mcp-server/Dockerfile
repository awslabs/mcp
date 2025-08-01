FROM python:3.10-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir uv

# Copy the package files
COPY . .

# Install the package
RUN uv pip install -e .

# Run the server
CMD ["python", "-m", "awslabs.elastic_beanstalk_mcp_server.main"]