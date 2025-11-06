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

FROM python:{{ cookiecutter.python_version }}-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    {{ cookiecutter.system_dependencies }} \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY awslabs ./awslabs
COPY docker-healthcheck.sh ./

# Make healthcheck script executable
RUN chmod +x docker-healthcheck.sh

# Install uv for faster dependency management
RUN pip install --no-cache-dir uv

# Install the package and its dependencies
RUN uv pip install --system --no-cache .

# Create application user and set ownership
RUN groupadd -r app && \
    useradd -r -g app -d /app -s /sbin/nologin app && \
    chown -R app:app /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FASTMCP_LOG_LEVEL=INFO

# Switch to non-root user
USER app

# Health check
HEALTHCHECK --interval={{ cookiecutter.healthcheck_interval }} --timeout={{ cookiecutter.healthcheck_timeout }} --start-period={{ cookiecutter.healthcheck_start_period }} --retries={{ cookiecutter.healthcheck_retries }} \
    CMD ["/app/docker-healthcheck.sh"]

# Run the server
ENTRYPOINT ["python", "-m", "{{ cookiecutter.module_path }}"]
