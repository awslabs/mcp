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

# dependabot should continue to update this to the latest hash.
FROM public.ecr.aws/amazonlinux/amazonlinux@sha256:a450a74bfebfa936e7106d79c8b4b4dd0ca891c790513f84624da02a0e5531db AS uv

# Install build dependencies needed for compiling packages
RUN dnf install -y shadow-utils python3 python3-devel gcc && \
    dnf clean all

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Prefer the system python
ENV UV_PYTHON_PREFERENCE=only-managed

# Run without updating the uv.lock file like running with `--frozen`
ENV UV_FROZEN=true

# Copy the required files first
COPY pyproject.toml uv.lock uv-requirements.txt ./

# Python optimization and uv configuration
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    python3 -m ensurepip && \
    python3 -m pip install --require-hashes --requirement uv-requirements.txt --no-cache-dir && \
    uv sync --python 3.13 --frozen --no-install-project --no-dev --no-editable

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --python 3.13 --frozen --no-dev --no-editable

# Make the directory just in case it doesn't exist
RUN mkdir -p /root/.local

FROM public.ecr.aws/amazonlinux/amazonlinux@sha256:a450a74bfebfa936e7106d79c8b4b4dd0ca891c790513f84624da02a0e5531db

# Place executables in the environment at the front of the path and include other binaries
ENV PATH="/app/.venv/bin:$PATH:/usr/sbin" \
    PYTHONUNBUFFERED=1

# Install other tools as needed for the MCP server
# Add non-root user and ability to change directory into /root
RUN dnf install -y shadow-utils procps && \
    dnf clean all && \
    groupadd --force --system app && \
    useradd app -g app -d /app && \
    chmod o+x /root

# Get the project from the uv layer
COPY --from=uv --chown=app:app /root/.local /root/.local
COPY --from=uv --chown=app:app /app/.venv /app/.venv

# Get healthcheck script
COPY ./docker-healthcheck.sh /usr/local/bin/docker-healthcheck.sh

# Run as non-root
USER app

# Network transport configuration (Phase 1).
#
# By default the server runs over stdio and binds nothing on the network, so no
# additional configuration is required. A network transport can be selected
# using only the documented environment variables below — the image and the
# ENTRYPOINT do not need to change:
#
#   MCP_TRANSPORT  Transport mode: stdio (default), streamable-http, or sse.
#   MCP_HOST       Bind address (default: 127.0.0.1, loopback only).
#   MCP_PORT       Bind port (default: 8000).
#   MCP_PATH       Request path (default: /mcp).
#
# To expose the server outside the container you MUST bind a non-loopback host
# (for example MCP_HOST=0.0.0.0) and publish the configured port (for example
# `-p 8000:8000`). Binding a non-loopback host exposes AWS access on the network
# and requires an external fronting authentication layer; the server performs no
# inbound authentication of its own in Phase 1. See the README section
# "Running the container with a network transport" for runnable examples.
#
# Example:
#   docker run \
#     -e MCP_TRANSPORT=streamable-http \
#     -e MCP_HOST=0.0.0.0 \
#     -e MCP_PORT=8000 \
#     -p 8000:8000 \
#     aws-healthomics-mcp-server

# Document the default network transport port. Publishing it still requires an
# explicit `-p`/`--publish` at run time; EXPOSE is documentation only.
EXPOSE 8000

# When running the container, add --db-path and a bind mount to the host's db file
HEALTHCHECK --interval=60s --timeout=10s --start-period=10s --retries=3 CMD ["docker-healthcheck.sh"]
ENTRYPOINT ["awslabs.aws-healthomics-mcp-server"]
