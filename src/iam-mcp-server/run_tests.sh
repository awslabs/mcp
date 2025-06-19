#!/bin/bash

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

set -e

echo "Running AWS IAM MCP Server tests..."

# Install dependencies
echo "Installing dependencies..."
uv sync --dev

# Run linting
echo "Running linting..."
uv run ruff check .
uv run ruff format --check .

# Run type checking
echo "Running type checking..."
uv run pyright

# Run tests
echo "Running tests..."
uv run pytest tests/ -v --cov=awslabs.iam_mcp_server --cov-report=term-missing

echo "All tests completed successfully!"
