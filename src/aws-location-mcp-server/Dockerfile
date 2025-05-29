# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

FROM public.ecr.aws/sam/build-python3.10@sha256:e78695db10ca8cb129e59e30f7dc9789b0dbd0181dba195d68419c72bac51ac1 AS uv

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

# Install the project's dependencies using the lockfile and settings
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    pip install uv && \
    uv sync --frozen --no-install-project --no-dev --no-editable

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# Make the directory just in case it doesn't exist
RUN mkdir -p /root/.local

FROM public.ecr.aws/sam/build-python3.10@sha256:e78695db10ca8cb129e59e30f7dc9789b0dbd0181dba195d68419c72bac51ac1

# Place executables in the environment at the front of the path and include other binaries
ENV PATH="/app/.venv/bin:$PATH:/usr/sbin"

# Install lsof for the healthcheck
# Install AWS CLI for AWS credentials management
# Add non-root user and ability to change directory into /root
RUN yum update -y && \
    yum install -y lsof && \
    yum clean all -y && \
    rm -rf /var/cache/yum && \
    groupadd --force --system app && \
    useradd app -g app -d /app && \
    chmod o+x /root

# Get the project from the uv layer
COPY --from=uv --chown=app:app /root/.local /root/.local
COPY --from=uv --chown=app:app /app/.venv /app/.venv

# Get healthcheck script
COPY ./docker-healthcheck.sh /usr/local/bin/docker-healthcheck.sh
RUN chmod +x /usr/local/bin/docker-healthcheck.sh

# Run as non-root
USER app

# AWS_REGION should be provided at runtime
# Example: docker run -e AWS_REGION=us-east-1 image_name

# Health check and entrypoint
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD [ "docker-healthcheck.sh" ]
ENTRYPOINT ["awslabs.aws-location-mcp-server"]
