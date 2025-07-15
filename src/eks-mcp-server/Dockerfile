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

FROM python:3.10-slim AS uv

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
COPY README.md .

# Install the project's dependencies using the lockfile and settings
COPY pyproject.toml uv.lock uv-requirements.txt ./
COPY . /app

RUN python -m venv /app/.venv \
 && /app/.venv/bin/pip install --upgrade pip \
 && /app/.venv/bin/pip install --no-cache-dir --require-hashes --requirement uv-requirements.txt \
 && /app/.venv/bin/pip install --no-cache-dir -e .

# Copy in your code and install the package


# Make the directory just in case it doesn't exist
RUN mkdir -p /root/.local

FROM python:3.10-slim

# Place executables in the environment at the front of the path and include other binaries
ENV PATH="/app/.venv/bin:$PATH:/usr/sbin"

# Install lsof for the healthcheck
# Install other tools as needed for the MCP server
# Add non-root user and ability to change directory into /root
RUN apt-get update \
  && apt-get install -y --no-install-recommends lsof \
  && rm -rf /var/lib/apt/lists/* \
  && groupadd --system app \
  && useradd --system --gid app --home-dir /app app \
  && mkdir -p /root/.local \
  && chmod o+x /root

# Get the project from the uv layer
COPY --from=uv --chown=app:app /root/.local /root/.local
COPY --from=uv --chown=app:app /app/.venv /app/.venv

# Get healthcheck script
COPY ./docker-healthcheck.sh /usr/local/bin/docker-healthcheck.sh

# Run as non-root
USER app

# When running the container, add --db-path and a bind mount to the host's db file
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD [ "docker-healthcheck.sh" ]
ENTRYPOINT ["awslabs.eks-mcp-server"]
