# Use a Python image with uv pre-installed
# 0.6.16-python3.10-bookworm-slim
FROM ghcr.io/astral-sh/uv@sha256:6d4d180306b85d5b222be0a5ab8ca2a0112583ebf47eeab485e4f792c129496e AS uv

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev --no-editable

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# Make the directory just in case it doesn't exist
RUN mkdir -p /root/.local

# python:3.10-slim-bookworm
FROM python@sha256:65c843653048a3ba22c8d5083a022f44aef774974f0f7f70cbf8cee4e931ac96

# Install lsof for the healthcheck
RUN apt-get update && apt-get install -y lsof && rm -rf /var/lib/apt/lists/*

RUN addgroup app && adduser --system --home /app --ingroup app --no-create-home --disabled-password --disabled-login app

COPY --from=uv --chown=app:app /root/.local /root/.local
COPY --from=uv --chown=app:app /app/.venv /app/.venv

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# So non-root can access /root/.local
RUN chmod o+x /root

# Copy the healthcheck script
COPY ./docker-healthcheck.sh /usr/local/bin/docker-healthcheck.sh

# Run as non-root
USER app

# when running the container, add --db-path and a bind mount to the host's db file
ENTRYPOINT ["awslabs.cdk-mcp-server"]

# Run a healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD [ "docker-healthcheck.sh" ]
