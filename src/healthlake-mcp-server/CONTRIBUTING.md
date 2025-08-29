# Contributing to HealthLake MCP Server

Thank you for your interest in contributing to the HealthLake MCP Server! This document provides guidelines for contributing to the project.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd healthlake-mcp-server
   ```

2. **Set up virtual environment**
   ```bash
   uv sync --dev
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install development dependencies**
   ```bash
   # Dependencies are already installed by uv sync --dev
   ```

## Development Workflow

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow the existing code style and patterns
   - Add unit tests for new functionality
   - Update documentation as needed

3. **Test your changes**
   ```bash
   make test          # Run unit tests
   make test-coverage # Run tests with coverage
   make lint          # Check code style
   make format        # Format code
   ```

4. **Commit and push**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   git push origin feature/your-feature-name
   ```

5. **Create a pull request**

### Code Style

- **Python**: Follow PEP 8 style guidelines
- **Formatting**: Use `black` and `isort` (run `make format`)
- **Linting**: Use `mypy` for type checking (run `make lint`)
- **Line length**: 88 characters (black default)

### Testing

- **Unit tests only**: We use fast, isolated unit tests without external dependencies
- **Test location**: Place tests in `tests/` directory
- **Test naming**: Use descriptive test function names starting with `test_`
- **Coverage**: Aim for good test coverage of new functionality

### Documentation

- **README**: Update if adding new features or changing installation
- **Docstrings**: Add docstrings to new functions and classes
- **Type hints**: Use type hints for all function parameters and return values

## Project Structure

```
awslabs/healthlake_mcp_server/
├── server.py           # MCP server implementation with tool handlers
├── fhir_operations.py  # AWS HealthLake client operations
├── main.py            # Entry point and CLI setup
└── __init__.py        # Package initialization

tests/
├── conftest.py        # Test fixtures
├── test_server.py     # Server creation tests
├── test_tool_handler.py # Tool dispatch logic tests
├── test_validation.py # Input validation tests
└── test_responses.py  # Response formatting tests
```

## Commit Message Guidelines

Use conventional commit format:

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Examples:
- `feat: add patient-everything operation`
- `fix: handle empty search results correctly`
- `docs: update installation instructions`

## Pull Request Guidelines

- **Title**: Use descriptive titles that explain the change
- **Description**: Provide context and explain what the PR does
- **Tests**: Ensure all tests pass
- **Documentation**: Update documentation if needed
- **Size**: Keep PRs focused and reasonably sized

## Getting Help

- **Questions**: Open an issue with the "question" label
- **Bugs**: Open an issue with the "bug" label and include reproduction steps
- **Features**: Open an issue with the "enhancement" label to discuss before implementing

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help maintain a welcoming environment for all contributors

Thank you for contributing!
