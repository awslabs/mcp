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

# Use a more standard Python 3.10 image to avoid version conflicts
FROM python:3.10-slim AS uv

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Prefer the system python
ENV UV_PYTHON_PREFERENCE=only-system

# Run without updating the uv.lock file like running with `--frozen`
ENV UV_FROZEN=true

# Copy the required files first
COPY pyproject.toml uv.lock ./

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev --no-editable

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# Production stage
FROM python:3.10-slim

# Install system dependencies for runtime
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Add non-root user
RUN groupadd --system app && \
    useradd --system --group app --home-dir /app app

# Create app directory
WORKDIR /app

# Get the project from the uv layer
COPY --from=uv --chown=app:app /app/.venv /app/.venv
COPY --from=uv --chown=app:app /app /app

# Set default connection pool configuration
ENV POSTGRES_POOL_MIN_SIZE="5"
ENV POSTGRES_POOL_MAX_SIZE="30"

# Run as non-root
USER app

# Expose the port (though MCP servers typically use stdio)
EXPOSE 8000

# Simple healthcheck that tests if the main script exists
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD test -f /app/awslabs/postgres_mcp_server/server.py || exit 1

# Use the correct module name
CMD ["python3", "-m", "awslabs.postgres_mcp_server.server"]
