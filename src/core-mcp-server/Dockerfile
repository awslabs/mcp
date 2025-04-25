# Use a Python image with uv pre-installed
# 0.6.16-python3.10-bookworm-slim
#FROM ghcr.io/astral-sh/uv@sha256:6d4d180306b85d5b222be0a5ab8ca2a0112583ebf47eeab485e4f792c129496e AS uv
# one option is to mimic https://github.com/astral-sh/uv/blob/main/Dockerfile

#TODO: match the `.python-version` and get the sha256 hash
#FROM public.ecr.aws/sam/build-python3.13:1.132.0-20241211194230 AS uv
#FROM public.ecr.aws/sam/build-python3.10:1.137.1-20250411084548 AS uv
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

# python:3.10-slim-bookworm
# TODO: find on ERC
#FROM python@sha256:65c843653048a3ba22c8d5083a022f44aef774974f0f7f70cbf8cee4e931ac96
#FROM public.ecr.aws/docker/library/python:3.10-slim-bookworm
#FROM public.ecr.aws/docker/library/python@sha256:65c843653048a3ba22c8d5083a022f44aef774974f0f7f70cbf8cee4e931ac96
FROM public.ecr.aws/sam/build-python3.10@sha256:04cdbe84bec08d17d621192bc3f0a9e4a85a83f2ac99aa9241659dfac0d845ea

RUN yum update -y && yum install -y lsof
# Install lsof for the healthcheck
#RUN apt-get update && apt-get install -y lsof && rm -rf /var/lib/apt/lists/*

ENV PATH="$PATH:/usr/sbin"

#RUN addgroup app && adduser --system --home /app --ingroup app --no-create-home --disabled-password --disabled-login app
RUN /usr/sbin/groupadd --force --system app && /usr/sbin/useradd app -g app -d /app

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
ENTRYPOINT ["awslabs.core-mcp-server"]

# Run a healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD [ "docker-healthcheck.sh" ]
