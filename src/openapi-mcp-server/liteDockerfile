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

# Stage 1: Build dependencies
FROM public.ecr.aws/docker/library/python:3.13.5-alpine3.21 AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies using virtual package for easy cleanup
RUN apk update && \
    apk add --no-cache --virtual .build-deps \
    build-base \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    cargo

WORKDIR /app

# Copy and install in single layer for better caching
COPY pyproject.toml uv.lock README.md LICENSE NOTICE ./
COPY awslabs ./awslabs
RUN pip install --no-cache-dir --target /opt/venv . && \
    # Remove unnecessary files to reduce image size
    find /opt/venv -name '*.pyc' -delete && \
    find /opt/venv -name '__pycache__' -delete

# Stage 2: Runtime image
FROM public.ecr.aws/docker/library/python:3.13.5-alpine3.21

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONWARNINGS="ignore"

# Install runtime dependencies and create user in single layer
RUN apk update && \
    apk add --no-cache ca-certificates && \
    update-ca-certificates && \
    addgroup -S app && \
    adduser -S app -G app -h /app

# Copy application files
COPY --from=builder --chown=app:app /opt/venv /opt/venv
COPY --from=builder --chown=app:app /app/awslabs /app/awslabs
COPY --chown=app:app ./docker-healthcheck.sh /usr/local/bin/docker-healthcheck.sh
RUN chmod +x /usr/local/bin/docker-healthcheck.sh

USER app
WORKDIR /app

# Optimize healthcheck intervals for better performance
HEALTHCHECK --interval=60s --timeout=10s --start-period=10s --retries=3 \
    CMD ["docker-healthcheck.sh"]

# Use exec form for better signal handling
ENTRYPOINT ["python", "-m", "awslabs.openapi_mcp_server.server"]
