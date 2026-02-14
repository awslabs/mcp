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

# OSS-Fuzz Dockerfile for AWS MCP Servers
# Based on OSS-Fuzz Python project guidelines:
# https://google.github.io/oss-fuzz/getting-started/new-project-guide/python-lang/

FROM gcr.io/oss-fuzz-base/base-builder-python

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for Python package management
RUN pip3 install uv

# Copy the entire repository
COPY . /src/mcp

WORKDIR /src/mcp

# Install Atheris for coverage-guided fuzzing
RUN pip3 install atheris

# Install Hypothesis for property-based testing
RUN pip3 install hypothesis

# Install pydantic for data models
RUN pip3 install pydantic

# Install the fuzzing package and its dependencies
RUN pip3 install -e /src/mcp/fuzzing

# Install MCP server packages that will be fuzzed
# These are installed in editable mode to enable coverage instrumentation
RUN pip3 install -e /src/mcp/src/postgres-mcp-server || true
RUN pip3 install -e /src/mcp/src/document-loader-mcp-server || true
RUN pip3 install -e /src/mcp/src/openapi-mcp-server || true
RUN pip3 install -e /src/mcp/src/dynamodb-mcp-server || true
RUN pip3 install -e /src/mcp/src/aws-api-mcp-server || true
RUN pip3 install -e /src/mcp/src/amazon-neptune-mcp-server || true
RUN pip3 install -e /src/mcp/src/aws-documentation-mcp-server || true
RUN pip3 install -e /src/mcp/src/amazon-mq-mcp-server || true
RUN pip3 install -e /src/mcp/src/amazon-sns-sqs-mcp-server || true
RUN pip3 install -e /src/mcp/src/core-mcp-server || true

# Copy the build script
COPY fuzzing/build.sh /src/mcp/fuzzing/build.sh

WORKDIR /src/mcp/fuzzing
