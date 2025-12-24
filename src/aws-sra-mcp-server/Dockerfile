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
FROM public.ecr.aws/docker/library/python:3.13-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_PREFERENCE=only-system \
    UV_FROZEN=true \
    PATH="/root/.local/bin:$PATH"

RUN mkdir -p /root/.local /root/.cache

WORKDIR /app

# Install uv and dependencies in single layer
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    apt-get remove -y curl && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock docker-healthcheck.sh LICENSE README.md /app/
COPY awslabs/ /app/awslabs/

RUN --mount=type=cache,target=/root/.cache/uv \
    /root/.local/bin/uv sync --frozen --no-install-project --no-dev --no-editable

RUN --mount=type=cache,target=/root/.cache/uv \
    /root/.local/bin/uv sync --frozen --no-dev --no-editable

FROM public.ecr.aws/docker/library/python:3.13-slim

ENV PATH="/app/.venv/bin:$PATH:/usr/sbin"

# Install lsof for the healthcheck
# Install other tools as needed for the MCP server
# Add non-root user and ability to change directory into /root
RUN apt-get update -y \
    && apt-get install -y lsof \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --force --system app \
    && useradd app -g app -d /app \
    && chmod o+x /root \
    && pip3 install fastmcp

# Copy only necessary files from builder, not the .venv folder
COPY --from=builder --chown=app:app /root/.local /root/.local
COPY --from=builder --chown=app:app /app/.venv/ /app/.venv
COPY --from=builder --chown=app:app --chmod=755 /app/docker-healthcheck.sh /usr/local/bin/

USER app
WORKDIR /app

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD ["/usr/local/bin/docker-healthcheck.sh"]

ENTRYPOINT ["aws-sra-mcp-server"]
