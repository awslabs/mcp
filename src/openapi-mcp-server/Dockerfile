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

# Build stage: Install dependencies and build application
FROM public.ecr.aws/docker/library/python:3.13.5-alpine3.21@sha256:c9a09c45a4bcc618c7f7128585b8dd0d41d0c31a8a107db4c8255ffe0b69375d AS builder

# Python optimization and uv configuration
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_PREFERENCE=only-system

# Install system dependencies and Python package manager
RUN apk update && \
    apk add --no-cache --virtual .build-deps \
    build-base \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    cargo && \
    pip install --no-cache-dir uv

WORKDIR /app

# Copy dependency manifests for layer caching optimization
COPY pyproject.toml ./
COPY uv.loc[k] uv-requirements.tx[t] ./
COPY requirements.tx[t] ./

# Install Python dependencies based on available dependency files
RUN if [ -f "uv.lock" ]; then \
        echo "Installing dependencies with uv lockfile" && \
        uv sync --python 3.13 --no-install-project --no-dev --no-editable; \
    elif [ -f "uv-requirements.txt" ]; then \
        echo "Installing dependencies with uv requirements" && \
        pip install --require-hashes --requirement uv-requirements.txt && \
        uv sync --python 3.13 --no-install-project --no-dev --no-editable; \
    elif [ -f "requirements.txt" ]; then \
        echo "Installing dependencies with pip requirements" && \
        python -m venv /app/.venv && \
        . /app/.venv/bin/activate && \
        pip install --no-cache-dir -r requirements.txt; \
    else \
        echo "Creating empty virtual environment" && \
        python -m venv /app/.venv; \
    fi

# Copy application source code and install package
COPY . /app
RUN if [ -f "uv.lock" ] || [ -f "uv-requirements.txt" ]; then \
        uv sync --python 3.13 --no-dev --no-editable; \
    else \
        . /app/.venv/bin/activate && \
        pip install --no-cache-dir --no-deps .; \
    fi && \
    find /app -name '*.pyc' -delete && \
    find /app -name '__pycache__' -delete

# Runtime stage: Minimal production image
FROM public.ecr.aws/docker/library/python:3.13.5-alpine3.21@sha256:c9a09c45a4bcc618c7f7128585b8dd0d41d0c31a8a107db4c8255ffe0b69375d

# Runtime environment configuration
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Install runtime dependencies and create application user
RUN apk update && \
    apk add --no-cache ca-certificates && \
    update-ca-certificates && \
    addgroup -S app && \
    adduser -S app -G app -h /app

# Copy application artifacts from build stage
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/awslabs /app/awslabs

# Install health check script
COPY --chown=app:app ./docker-healthcheck.sh /usr/local/bin/docker-healthcheck.sh
RUN chmod +x /usr/local/bin/docker-healthcheck.sh

# Switch to non-root user for security
USER app
WORKDIR /app

# Configure container health monitoring
HEALTHCHECK --interval=60s --timeout=10s --start-period=10s --retries=3 \
    CMD ["docker-healthcheck.sh"]

# Define application entry point
ENTRYPOINT ["python", "-m", "awslabs.openapi_mcp_server.server"]
