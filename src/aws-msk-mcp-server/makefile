.PHONY: all test lint fix clean help

# Default target - runs tests and linting
all: test lint

# Run tests with verbose output
test:
	uv run pytest tests/ -v

# Check code compliance with ruff and apply fixes
lint:
	uv run --frozen ruff check .
	uv run --frozen ruff format --check --diff .

# Automatically fix all fixable ruff issues
fix:
	uv run --frozen ruff check --fix .
		uv run --frozen ruff format .

# Clean up Python cache files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

# Display help information
help:
	@echo "Available targets:"
	@echo "  all     - Run tests and linting (default)"
	@echo "  test    - Run pytest tests"
	@echo "  lint    - Run ruff linting "
	@echo "  fix     - Automatically fix all fixable ruff issues"
	@echo "  clean   - Clean up Python cache files"
	@echo "  help    - Show this help message"
