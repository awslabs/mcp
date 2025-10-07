# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# AWS DMS MCP Server Dockerfile
# Multi-stage build for minimal production image

# Build stage
FROM python:3.13-slim AS builder

WORKDIR /build

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv

# Copy package files
COPY pyproject.toml README.md ./
COPY awslabs/ ./awslabs/

# Install dependencies
RUN uv pip install --system --no-cache .

# Production stage
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY awslabs/ ./awslabs/

# Create non-root user
RUN useradd -m -u 1000 mcp && \
    chown -R mcp:mcp /app

USER mcp

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DMS_LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from awslabs.aws_dms_mcp_server import __version__; print(__version__)" || exit 1

# Expose MCP server port (if applicable)
# EXPOSE 8080

# Entry point
ENTRYPOINT ["awslabs.aws-dms-mcp-server"]

# Default command (can be overridden)
CMD []
