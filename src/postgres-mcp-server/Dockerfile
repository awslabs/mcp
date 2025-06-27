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

FROM public.ecr.aws/sam/build-python3.10@sha256:d821662474d65f3cf2fc97dba2fa807a3adb580d02895fc4545527812550ea65

# Install the project into `/app`
WORKDIR /app

# Copy all project files
COPY . /app

# Install dependencies with pip (avoiding uv version conflicts)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -e .

# Install lsof for the healthcheck
RUN yum update -y && \
    yum install -y lsof && \
    yum clean all -y && \
    rm -rf /var/cache/yum

# Get healthcheck script
COPY ./docker-healthcheck.sh /usr/local/bin/docker-healthcheck.sh
RUN chmod +x /usr/local/bin/docker-healthcheck.sh

# Set default connection pool configuration
ENV POSTGRES_POOL_MIN_SIZE="5"
ENV POSTGRES_POOL_MAX_SIZE="30"

# Expose the port
EXPOSE 8000

# When running the container, add --db-path and a bind mount to the host's db file
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD [ "docker-healthcheck.sh" ]

# Use the correct module name (fixed from postgresql_mcp_server to postgres_mcp_server)
CMD ["python3", "-m", "awslabs.postgres_mcp_server.server"]
