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

# ---------------------------------------------------------------------------
# Harness deployment image for the remote-deployment integration tests
# (AgentCore_Deployment, Req 2.1).
#
# This image packages the *unmodified* AWS HealthOmics MCP Server and starts it
# through the harness-owned entrypoint (integration/deploy/image/entrypoint.py),
# which imports the server's `mcp` instance + `main`, registers the read-only
# `WhoAmI` isolation tool, and calls `main()`. No server-package source is
# modified.
#
# It mirrors the project's root Dockerfile conventions: the same amazonlinux
# base, a multi-stage uv-based dependency install, and a non-root `app` user.
# The difference is that this image also copies the `integration/` package into
# the final stage (the root image installs only the server package into the
# venv) and starts the harness entrypoint module instead of the console script.
#
# BUILD CONTEXT: this Dockerfile MUST be built from the PROJECT ROOT so the
# server sources, lockfiles, and the integration/ package are all in context:
#
#   docker build -f integration/deploy/image/Dockerfile -t aho-mcp-itest .
#
# PORT / TRANSPORT (Req 2.1): AgentCore Runtime routes inbound MCP traffic to
# the container on port 8080 (the standard AgentCore container port), so the
# server is started with the streamable-http transport bound to 0.0.0.0:8080.
# The server binds 0.0.0.0 (not the loopback default) because AgentCore's
# managed ingress reaches the container over its network interface; AgentCore
# Runtime is the sole network-reachable ingress (Req 2.4), so the container port
# is never otherwise exposed. The server emits its expected non-loopback
# exposure warning; inbound authentication is terminated at the AgentCore
# boundary.
#
# Multi-tenant/JWT settings (MCP_MULTI_TENANT, MCP_INBOUND_AUTH,
# MCP_JWT_ROLE_REGISTRY) are injected at deploy time by the AgentCore deployment
# (task 10.1), not baked into the image. The image's responsibility per Req 2.1
# is the transport + port binding.
# ---------------------------------------------------------------------------

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

# Place executables in the environment at the front of the path and include other binaries.
# PYTHONPATH=/app makes the harness `integration` package importable alongside the
# server package installed in the venv, so `python -m integration.deploy.image.entrypoint`
# resolves both `awslabs...` (from the venv) and `integration...` (from /app).
ENV PATH="/app/.venv/bin:$PATH:/usr/sbin" \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install other tools as needed for the MCP server
# Add non-root user and ability to change directory into /root
RUN dnf install -y shadow-utils procps && \
    dnf clean all && \
    groupadd --force --system app && \
    useradd app -g app -d /app && \
    chmod o+x /root

# Get the project (installed server package) from the uv layer
COPY --from=uv --chown=app:app /root/.local /root/.local
COPY --from=uv --chown=app:app /app/.venv /app/.venv

# Copy the harness `integration` package into the final image. The root image
# installs only the server package into the venv; the harness entrypoint and its
# package tree are not installed, so they must be present on PYTHONPATH here.
COPY --chown=app:app integration /app/integration

# Harness entrypoint transport configuration (Req 2.1).
# Start the server over streamable-http at the AgentCore MCP container address. AgentCore
# routes inbound MCP traffic to the container at the fixed 0.0.0.0:8000/mcp, so the server
# must bind port 8000 and serve /mcp.
ENV MCP_TRANSPORT=streamable-http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000 \
    MCP_PATH=/mcp

# The server listens on the AgentCore container port.
WORKDIR /app

# Run as non-root
USER app

# Document the AgentCore container port. Publishing/routing is handled by
# AgentCore Runtime; EXPOSE is documentation only.
EXPOSE 8000

# Health check: confirm the server is accepting TCP connections on the configured
# streamable-http port. Uses the venv python (no extra tooling required).
HEALTHCHECK --interval=60s --timeout=10s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import os,socket,sys; s=socket.socket(); s.settimeout(5); sys.exit(0 if s.connect_ex(('127.0.0.1', int(os.environ.get('MCP_PORT','8000'))))==0 else 1)"]

# Start the harness entrypoint: it imports the unmodified server `mcp` instance,
# registers the read-only `WhoAmI` tool, then calls the server's `main()`, which
# starts the streamable-http transport on MCP_HOST:MCP_PORT.
ENTRYPOINT ["python", "-m", "integration.deploy.image.entrypoint"]
