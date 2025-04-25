#FROM public.ecr.aws/sam/build-python3.10:1.137.1-20250411084548
FROM public.ecr.aws/sam/build-python3.10@sha256:04cdbe84bec08d17d621192bc3f0a9e4a85a83f2ac99aa9241659dfac0d845ea AS uv

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
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    pip install uv && \
    uv sync --frozen --no-install-project --no-dev --no-editable

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# Make the directory just in case it doesn't exist
RUN mkdir -p /root/.local

FROM public.ecr.aws/sam/build-python3.10@sha256:04cdbe84bec08d17d621192bc3f0a9e4a85a83f2ac99aa9241659dfac0d845ea

# Place executables in the environment at the front of the path and include other binaries
ENV PATH="/app/.venv/bin:$PATH:/usr/sbin"

# Install lsof for the healthcheck
# Install other tools as needed for the MCP server
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

# Run as non-root
USER app

# When running the container, add --db-path and a bind mount to the host's db file
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD [ "docker-healthcheck.sh" ]
ENTRYPOINT ["awslabs.cdk-mcp-server"]
