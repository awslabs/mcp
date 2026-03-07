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

# Build stage
FROM public.ecr.aws/docker/library/python:3.12-alpine AS builder

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    python3-dev \
    cargo

# Install uv for faster dependency installation
ADD --chmod=755 https://astral.sh/uv/install.sh /install.sh
RUN /install.sh && rm /install.sh

# Create app directory
WORKDIR /app

# Copy dependency files and source code
COPY pyproject.toml ./
COPY awslabs ./awslabs

# Create virtual environment and install dependencies
RUN /root/.local/bin/uv venv .venv && \
    /root/.local/bin/uv pip install --python .venv/bin/python .

# Final stage
FROM public.ecr.aws/docker/library/python:3.12-alpine

# Install runtime dependencies
RUN apk add --no-cache \
    ca-certificates \
    && update-ca-certificates

# Create non-root user
RUN addgroup -S app && \
    adduser -S app -G app -h /app

# Copy virtual environment from builder
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Copy application code
COPY --chown=app:app awslabs /app/awslabs
COPY --chown=app:app docker-healthcheck.sh /usr/local/bin/docker-healthcheck.sh

# Make healthcheck executable
RUN chmod +x /usr/local/bin/docker-healthcheck.sh

# Set environment
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER app
WORKDIR /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["/usr/local/bin/docker-healthcheck.sh"]

# Run the server
ENTRYPOINT ["python", "-m", "awslabs.mwaa_mcp_server"]
