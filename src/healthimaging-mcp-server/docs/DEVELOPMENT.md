# Development Guide

This guide covers development setup, workflows, and best practices for contributing to the AWS HealthImaging MCP Server.

## Development Environment Setup

### Prerequisites

- Python 3.10 or higher
- Git
- AWS account with HealthImaging access
- Code editor (VS Code recommended)

### Initial Setup

1. **Clone the repository**
```bash
git clone https://github.com/awslabs/healthimaging-mcp-server.git
cd healthimaging-mcp-server
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install development dependencies**
```bash
pip install -e ".[dev]"
# Or using make
make install-dev
```

4. **Configure AWS credentials**
```bash
aws configure
```

## Project Structure

```
healthimaging-mcp-server/
├── .github/
│   └── workflows/          # GitHub Actions CI/CD
│       ├── test.yml        # Test workflow
│       └── publish.yml     # PyPI publish workflow
├── docs/                   # Documentation
│   ├── API.md             # API reference
│   ├── ARCHITECTURE.md    # Architecture overview
│   ├── QUICKSTART.md      # Quick start guide
│   └── DEVELOPMENT.md     # This file
├── examples/              # Usage examples
│   └── example_usage.py
├── src/
│   └── awslabs/
│       └── healthimaging_mcp_server/
│           ├── __init__.py    # Package initialization
│           ├── server.py      # MCP server implementation
│           └── tools.py       # Tool implementations
├── tests/                 # Test suite
│   ├── conftest.py       # Pytest fixtures
│   ├── test_server.py    # Server tests
│   └── test_tools.py     # Tool tests
├── .gitignore            # Git ignore rules
├── CHANGELOG.md          # Version history
├── CONTRIBUTING.md       # Contribution guidelines
├── LICENSE               # Apache 2.0 license
├── Makefile              # Development commands
├── pyproject.toml        # Project configuration
├── README.md             # Main documentation
├── requirements.txt      # Core dependencies
├── requirements-dev.txt  # Dev dependencies
└── SECURITY.md           # Security policy
```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/my-new-feature
```

### 2. Make Changes

Edit files in `src/awslabs/healthimaging_mcp_server/`

### 3. Run Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
pytest tests/test_tools.py -v
```

### 4. Format Code

```bash
# Format with black
make format

# Or manually
black src/ tests/
```

### 5. Lint Code

```bash
# Run linting
make lint

# Fix auto-fixable issues
ruff check --fix src/ tests/
```

### 6. Type Check

```bash
# Run mypy
make type-check
```

### 7. Commit Changes

```bash
git add .
git commit -m "feat: add new feature"
```

Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `test:` Tests
- `refactor:` Code refactoring
- `chore:` Maintenance

### 8. Push and Create Pull Request

```bash
git push origin feature/my-new-feature
```

Then create a Pull Request on GitHub.

## Adding New Tools

### Step 1: Define the Tool

Add to `src/awslabs/healthimaging_mcp_server/tools.py`:

```python
@server.tool()
async def my_new_tool(
    param1: str,
    param2: Optional[int] = None
) -> str:
    """
    Brief description of the tool.

    Args:
        param1: Description of param1
        param2: Description of param2 (optional)

    Returns:
        JSON string containing results
    """
    try:
        client = get_healthimaging_client()
        response = client.my_api_call(
            Param1=param1,
            Param2=param2
        )
        return json.dumps(response, indent=2, default=str)
    except ClientError as e:
        logger.error(f"Error in my_new_tool: {e}")
        return json.dumps({"error": str(e)})
```

### Step 2: Add Tool Definition

Add to the return list in `register_tools()`:

```python
{
    "name": "my_new_tool",
    "description": "Brief description",
    "inputSchema": {
        "type": "object",
        "properties": {
            "param1": {
                "type": "string",
                "description": "Description"
            },
            "param2": {
                "type": "integer",
                "description": "Description"
            }
        },
        "required": ["param1"]
    }
}
```

### Step 3: Add Tests

Add to `tests/test_tools.py`:

```python
@pytest.mark.asyncio
async def test_my_new_tool(server):
    """Test my new tool."""
    with patch("awslabs.healthimaging_mcp_server.tools.boto3.client") as mock_client:
        mock_hi = MagicMock()
        mock_hi.my_api_call.return_value = {"result": "success"}
        mock_client.return_value = mock_hi

        register_tools(server)

        tools = [t for t in server._tool_handlers.keys()]
        assert "my_new_tool" in tools
```

### Step 4: Update Documentation

- Add to `docs/API.md`
- Update `README.md` if needed
- Add example to `examples/`

## Testing

### Running Tests

```bash
# All tests
pytest

# Specific file
pytest tests/test_tools.py

# Specific test
pytest tests/test_tools.py::test_list_datastores

# With coverage
pytest --cov=awslabs.healthimaging_mcp_server

# Coverage report
pytest --cov=awslabs.healthimaging_mcp_server --cov-report=html
open htmlcov/index.html
```

### Writing Tests

Use pytest fixtures from `conftest.py`:

```python
@pytest.mark.asyncio
async def test_something(server, mock_healthimaging_client, sample_datastore):
    # Your test code
    pass
```

### Mocking AWS Calls

Always mock boto3 clients:

```python
with patch("awslabs.healthimaging_mcp_server.tools.boto3.client") as mock_client:
    mock_hi = MagicMock()
    mock_hi.some_method.return_value = {"data": "value"}
    mock_client.return_value = mock_hi

    # Test code
```

## Code Quality

### Black (Formatting)

Configuration in `pyproject.toml`:
```toml
[tool.black]
line-length = 100
target-version = ["py310"]
```

Run: `black src/ tests/`

### Ruff (Linting)

Configuration in `pyproject.toml`:
```toml
[tool.ruff]
line-length = 100
target-version = "py310"
```

Run: `ruff check src/ tests/`

### Mypy (Type Checking)

Configuration in `pyproject.toml`:
```toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

Run: `mypy src/`

## Local Testing with MCP Client

### 1. Install Locally

```bash
pip install -e .
```

### 2. Configure MCP Client

Add to Claude Desktop config:

```json
{
  "mcpServers": {
    "healthimaging-dev": {
      "command": "python",
      "args": ["-m", "awslabs.healthimaging_mcp_server.server"],
      "cwd": "/path/to/healthimaging-mcp-server",
      "env": {
        "AWS_REGION": "us-east-1",
        "PYTHONPATH": "/path/to/healthimaging-mcp-server/src"
      }
    }
  }
}
```

### 3. Test Changes

Restart Claude Desktop and test your changes.

## Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Print Debugging

```python
logger.debug(f"Variable value: {variable}")
```

### VS Code Debugging

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: MCP Server",
      "type": "python",
      "request": "launch",
      "module": "awslabs.healthimaging_mcp_server.server",
      "console": "integratedTerminal"
    }
  ]
}
```

## Building and Publishing

### Build Package

```bash
make build
# Or
python -m build
```

### Test Package Locally

```bash
pip install dist/awslabs.healthimaging_mcp_server-0.1.0-py3-none-any.whl
```

### Publish to PyPI

```bash
make publish
# Or
python -m twine upload dist/*
```

### Publish to Test PyPI

```bash
python -m twine upload --repository testpypi dist/*
```

## Continuous Integration

### GitHub Actions

Workflows in `.github/workflows/`:

- **test.yml**: Runs on push/Pull Request
  - Tests on Python 3.10, 3.11, 3.12
  - Linting and formatting checks
  - Type checking
  - Coverage reporting

- **publish.yml**: Runs on release
  - Builds package
  - Publishes to PyPI

### Running CI Locally

Use [act](https://github.com/nektos/act):

```bash
act -j test
```

## Documentation

### Building Docs

Documentation is in Markdown format in `docs/`.

### Updating API Docs

When adding/changing tools, update:
- `docs/API.md` - Tool reference
- `README.md` - Overview
- `examples/` - Usage examples

### Documentation Style

- Use clear, concise language
- Include code examples
- Add parameter descriptions
- Document return values
- Note any limitations

## Performance Optimization

### Profiling

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Code to profile

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats()
```

### Memory Profiling

```bash
pip install memory-profiler
python -m memory_profiler src/awslabs/healthimaging_mcp_server/server.py
```

## Troubleshooting

### Import Errors

```bash
# Ensure package is installed in editable mode
pip install -e .

# Check PYTHONPATH
echo $PYTHONPATH
```

### Test Failures

```bash
# Run with verbose output
pytest -vv

# Run with print statements
pytest -s

# Run specific test
pytest tests/test_tools.py::test_list_datastores -vv
```

### AWS Credential Issues

```bash
# Verify credentials
aws sts get-caller-identity

# Check region
aws configure get region
```

## Best Practices

1. **Write tests first** (TDD approach)
2. **Keep functions small** and focused
3. **Use type hints** everywhere
4. **Document all public APIs**
5. **Handle errors gracefully**
6. **Log important events**
7. **Follow PEP 8** style guide
8. **Keep dependencies minimal**
9. **Version bump** appropriately
10. **Update CHANGELOG.md**

## Resources

- [MCP Specification](https://modelcontextprotocol.io/)
- [AWS HealthImaging API](https://docs.aws.amazon.com/healthimaging/latest/APIReference/)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [pytest Documentation](https://docs.pytest.org/)
- [Black Documentation](https://black.readthedocs.io/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)

## Getting Help

- Open an issue on GitHub
- Check existing issues and PRs
- Review documentation
- Ask in discussions

## License

This project is licensed under Apache License 2.0. See [LICENSE](../LICENSE) for details.
