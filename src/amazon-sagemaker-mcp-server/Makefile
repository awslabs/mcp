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

# Makefile for Amazon SageMaker MCP Server

.PHONY: help test test-verbose test-coverage test-server test-utils install-dev lint format clean

# Default target
help:
	@echo "Available targets:"
	@echo "  test          - Run all tests"
	@echo "  test-verbose  - Run all tests with verbose output"
	@echo "  test-coverage - Run all tests with coverage report"
	@echo "  test-server   - Run only server tests"
	@echo "  test-utils    - Run only utils tests"
	@echo "  install-dev   - Install development dependencies"
	@echo "  lint          - Run linting checks"
	@echo "  format        - Format code"
	@echo "  clean         - Clean up generated files"

# Test targets
test:
	python -m pytest tests/ --tb=short

test-verbose:
	python -m pytest tests/ -v --tb=short

test-coverage:
	python -m pytest tests/ --cov=awslabs.amazon_sagemaker_mcp_server --cov-report=term-missing --cov-report=html --tb=short

test-server:
	python -m pytest tests/test_server.py -v --tb=short

test-utils:
	python -m pytest tests/test_aws_client.py tests/test_permissions.py tests/test_utils.py -v --tb=short

# Development targets
install-dev:
	uv sync --group dev

lint:
	ruff check .
	pyright .

format:
	ruff format .

# Clean up
clean:
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
