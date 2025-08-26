.PHONY: install install-dev test lint format clean run build help

# Install the package
install:
	uv pip install -e .

# Install with development dependencies
install-dev:
	uv pip install -e ".[dev]"

# Run unit tests
test:
	uv run pytest tests/ -v

# Run unit tests with coverage
test-coverage:
	uv run pytest tests/ -v --cov=awslabs/healthlake_mcp_server --cov-report=html --cov-report=term

# Run linting
lint:
	uv run ruff check awslabs/ tests/
	uv run pyright awslabs/

# Run security checks
security:
	uv run bandit -r awslabs/

# Run all checks
check: lint security

# Format code
format:
	uv run ruff format awslabs/ tests/
	uv run ruff check --fix awslabs/ tests/

# Clean build artifacts and cache files
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf awslabs/*.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*~" -delete
	find . -type f -name ".coverage" -delete

# Run the MCP server
run:
	uv run awslabs.healthlake-mcp-server

# Build package
build:
	uv build

# Generate uv lock file
lock:
	uv lock

# Show help
help:
	@echo "Available commands:"
	@echo "  install       - Install the package in development mode"
	@echo "  install-dev   - Install with development dependencies"
	@echo "  test          - Run unit tests"
	@echo "  test-coverage - Run unit tests with coverage report"
	@echo "  lint          - Run code linting"
	@echo "  format        - Format code with black and isort"
	@echo "  clean         - Clean build artifacts and cache files"
	@echo "  run           - Run the MCP server"
	@echo "  build         - Build the package"
	@echo "  lock          - Generate uv.lock file"
	@echo "  help          - Show this help message"
