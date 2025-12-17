# Contributing to AWS HealthImaging MCP Server

Thank you for your interest in contributing to the AWS HealthImaging MCP Server! This document provides guidelines and instructions for contributing.

## Code of Conduct

This project adheres to the Amazon Open Source Code of Conduct. By participating, you are expected to uphold this code.

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, include:

- A clear and descriptive title
- Detailed steps to reproduce the issue
- Expected behavior vs actual behavior
- Your environment (OS, Python version, AWS region)
- Any relevant logs or error messages

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- A clear and descriptive title
- Detailed description of the proposed functionality
- Use cases and examples
- Any potential implementation approaches

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add or update tests as needed
5. Ensure all tests pass (`pytest`)
6. Format your code (`black src/ tests/`)
7. Run linting (`ruff check src/ tests/`)
8. Commit your changes (`git commit -m 'Add amazing feature'`)
9. Push to the branch (`git push origin feature/amazing-feature`)
10. Open a Pull Request

## Development Setup

### Prerequisites

- Python 3.10 or higher
- pip or uv package manager
- AWS account with HealthImaging access

### Setup

```bash
# Clone the repository
git clone https://github.com/awslabs/healthimaging-mcp-server.git
cd healthimaging-mcp-server

# Install in development mode
pip install -e ".[dev]"

# Or using uv
uv pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=awslabs.healthimaging_mcp_server

# Run specific test file
pytest tests/test_server.py
```

### Code Style

We use:
- **Black** for code formatting (line length: 100)
- **Ruff** for linting
- **mypy** for type checking

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/
```

## Project Structure

```
healthimaging-mcp-server/
├── src/
│   └── awslabs/
│       └── healthimaging_mcp_server/
│           ├── __init__.py
│           ├── server.py      # Main MCP server
│           ├── tools.py       # Tool implementations
│           └── models.py      # Data models
├── tests/
│   ├── test_server.py
│   ├── test_tools.py
│   └── conftest.py
├── examples/
│   └── example_usage.py
├── pyproject.toml
├── README.md
└── CONTRIBUTING.md
```

## Adding New Tools

When adding a new tool:

1. Define the tool in `src/awslabs/healthimaging_mcp_server/tools.py`
2. Add corresponding tests in `tests/test_tools.py`
3. Update documentation in `README.md`
4. Add usage examples if applicable

Example tool structure:

```python
@server.tool()
async def my_new_tool(
    param1: str,
    param2: int = 10
) -> str:
    """
    Brief description of what the tool does.

    Args:
        param1: Description of param1
        param2: Description of param2 (default: 10)

    Returns:
        Description of return value
    """
    # Implementation
    return result
```

## Testing Guidelines

- Write tests for all new functionality
- Maintain or improve code coverage
- Use mocking for AWS API calls
- Include both positive and negative test cases
- Test edge cases and error handling

## Documentation

- Update README.md for user-facing changes
- Add docstrings to all functions and classes
- Include type hints
- Provide usage examples for new features

## Commit Messages

Follow conventional commit format:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test additions or changes
- `refactor:` Code refactoring
- `chore:` Maintenance tasks

Example: `feat: add support for image frame caching`

## Review Process

All submissions require review. We use GitHub pull requests for this purpose. The review process includes:

1. Automated checks (tests, linting, type checking)
2. Code review by maintainers
3. Discussion and iteration as needed
4. Approval and merge

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

## Questions?

Feel free to open an issue for any questions or concerns about contributing.
