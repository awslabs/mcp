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


.PHONY: help install lint format test test-cov test-fast clean build publish dev

# Default target
.DEFAULT_GOAL := help

# Python and package management
PYTHON := python
UV := uv
PYTEST := pytest
RUFF := ruff

# Directories
SRC_DIR := awslabs
TEST_DIR := tests

help: ## Show this help message
	@echo "DynamoDB MCP Server - Development Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies with uv
	$(UV) sync

install-dev: ## Install development dependencies
	$(UV) sync --all-extras

lint: ## Run linting checks (ruff)
	$(RUFF) check $(SRC_DIR) $(TEST_DIR) --exclude "awslabs/dynamodb_mcp_server/cost_performance/load_test_assets"

lint-fix: ## Run linting with auto-fix
	$(RUFF) check --fix $(SRC_DIR) $(TEST_DIR) --exclude "awslabs/dynamodb_mcp_server/cost_performance/load_test_assets"

format: ## Format code with ruff
	$(RUFF) format $(SRC_DIR) $(TEST_DIR) --exclude "awslabs/dynamodb_mcp_server/cost_performance/load_test_assets"

format-check: ## Check code formatting without changes
	$(RUFF) format --check $(SRC_DIR) $(TEST_DIR) --exclude "awslabs/dynamodb_mcp_server/cost_performance/load_test_assets"

test: ## Run all tests
	$(PYTEST) $(TEST_DIR) -v

test-cov: ## Run tests with coverage report
	$(PYTEST) $(TEST_DIR) -v --cov=$(SRC_DIR) --cov-report=term-missing --cov-report=html

test-fast: ## Run tests without coverage (faster)
	$(PYTEST) $(TEST_DIR) -v -x

test-watch: ## Run tests in watch mode
	$(PYTEST) $(TEST_DIR) -v --looponfail

test-specific: ## Run specific test file (usage: make test-specific FILE=test_file.py)
	$(PYTEST) $(TEST_DIR)/$(FILE) -v

clean: ## Clean build artifacts and cache
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

build: clean ## Build package
	$(UV) build

check: lint format-check test ## Run all checks (lint, format, test)

ci: ## Run CI pipeline (format, lint, test with coverage)
	@echo "Running CI pipeline..."
	@$(MAKE) format-check
	@$(MAKE) lint
	@$(MAKE) test-cov
	@echo "✅ CI pipeline completed successfully"

# Full validation before commit
validate: clean format lint test-cov ## Full validation (clean, format, lint, test with coverage)
	@echo "✅ All validations passed - ready to commit"
