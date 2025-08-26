.PHONY: test lint format security clean run build

# Run tests
test:
	uv run pytest tests/ -v

# Run tests with coverage
test-cov:
	uv run pytest tests/ -v --cov=awslabs/healthlake_mcp_server --cov-report=term

# Run linting
lint:
	uv run ruff check awslabs/ tests/
	uv run pyright awslabs/

# Format code
format:
	uv run ruff format awslabs/ tests/
	uv run ruff check --fix awslabs/ tests/

# Security checks
security:
	uv run bandit -r awslabs/

# Run all checks
check: lint security

# Clean artifacts
clean:
	rm -rf build/ dist/ *.egg-info/ htmlcov/ .pytest_cache/
	find . -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Run server
run:
	uv run awslabs.healthlake-mcp-server

# Build package
build:
	uv build
