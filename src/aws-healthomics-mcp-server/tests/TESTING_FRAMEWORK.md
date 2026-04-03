# AWS HealthOmics MCP Server - Testing Framework Guide

## Overview

The AWS HealthOmics MCP Server uses a comprehensive testing framework built on **pytest** with specialized utilities for testing MCP (Model Context Protocol) tools. This guide covers setup, execution, and best practices for the testing framework.

## Table of Contents

- [Quick Start](#quick-start)
- [Test Framework Architecture](#test-framework-architecture)
- [Setup and Installation](#setup-and-installation)
- [Running Tests](#running-tests)
- [Test Categories](#test-categories)
- [Writing Tests](#writing-tests)
- [MCP Tool Testing](#mcp-tool-testing)
- [Test Utilities](#test-utilities)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Quick Start

```bash
# Navigate to the project directory
cd src/aws-healthomics-mcp-server

# Install dependencies (if not already installed)
pip install -e .

# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=awslabs.aws_healthomics_mcp_server --cov-report=html

# Run specific test categories
python -m pytest tests/test_models.py -v                    # Model tests
python -m pytest tests/test_workflow_*.py -v               # Workflow tests
python -m pytest tests/test_genomics_*_working.py -v       # Integration tests
```

## Test Framework Architecture

### Core Components

```
tests/
├── conftest.py                                    # Shared fixtures and configuration
├── test_helpers.py                               # MCP tool testing utilities
├── fixtures/                                     # Test data fixtures
├── TESTING_FRAMEWORK.md                         # This documentation
├── INTEGRATION_TEST_SOLUTION.md                 # MCP Field annotation solution
└── test_*.py                                    # Test modules
```

### Test Categories

| Category | Files | Purpose | Count |
|----------|-------|---------|-------|
| **Unit Tests** | `test_models.py`, `test_aws_utils.py`, etc. | Core functionality | 500+ |
| **Integration Tests** | `test_genomics_*_working.py` | End-to-end workflows | 8 |
| **Workflow Tests** | `test_workflow_*.py` | Workflow management | 200+ |
| **Utility Tests** | `test_*_utils.py` | Helper functions | 50+ |

## Setup and Installation

### Prerequisites

- Python 3.10+
- pip or uv package manager

### Installation

```bash
# Clone the repository (if not already done)
git clone <repository-url>
cd src/aws-healthomics-mcp-server

# Install in development mode with test dependencies
pip install -e ".[dev]"

# Or using uv
uv pip install -e ".[dev]"
```

### Dependencies

The test framework uses these key dependencies:

```toml
[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.26.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.12.0",
]
```

## Running Tests

### Basic Test Execution

```bash
# Run all tests
python -m pytest tests/

# Run with verbose output
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=awslabs.aws_healthomics_mcp_server

# Run specific test file
python -m pytest tests/test_models.py -v

# Run specific test method
python -m pytest tests/test_models.py::test_workflow_summary -v
```

### Test Filtering

```bash
# Run tests by marker
python -m pytest -m "not integration" tests/

# Run tests by pattern
python -m pytest -k "workflow" tests/

# Run failed tests only
python -m pytest --lf tests/

# Run tests in parallel (if pytest-xdist installed)
python -m pytest -n auto tests/
```

### Coverage Reports

```bash
# Generate HTML coverage report
python -m pytest tests/ --cov=awslabs.aws_healthomics_mcp_server --cov-report=html

# Generate terminal coverage report
python -m pytest tests/ --cov=awslabs.aws_healthomics_mcp_server --cov-report=term-missing

# Coverage with minimum threshold
python -m pytest tests/ --cov=awslabs.aws_healthomics_mcp_server --cov-fail-under=80
```

## Test Categories

### 1. Unit Tests

**Purpose**: Test individual functions and classes in isolation.

**Examples**:
- `test_models.py` - Pydantic model validation
- `test_aws_utils.py` - AWS utility functions
- `test_pattern_matcher.py` - Pattern matching logic

**Characteristics**:
- Fast execution (< 1 second each)
- No external dependencies
- Comprehensive mocking
- High code coverage

### 2. Integration Tests

**Purpose**: Test end-to-end workflows with proper MCP tool integration.

**Examples**:
- `test_genomics_file_search_integration_working.py` - Genomics search workflows

**Characteristics**:
- Uses `MCPToolTestWrapper` for MCP Field handling
- Comprehensive mocking of AWS services
- Tests complete user workflows
- Validates response structures

### 3. Workflow Tests

**Purpose**: Test workflow management, execution, and analysis.

**Examples**:
- `test_workflow_management.py` - Workflow CRUD operations
- `test_workflow_execution.py` - Workflow execution logic
- `test_workflow_linting.py` - Workflow validation

### 4. Utility Tests

**Purpose**: Test helper functions and utilities.

**Examples**:
- `test_s3_utils.py` - S3 utility functions
- `test_scoring_engine.py` - File scoring algorithms
- `test_pagination.py` - Pagination utilities

## Writing Tests

### Basic Test Structure

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

class TestYourFeature:
    """Test class for your feature."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        context = AsyncMock()
        context.error = AsyncMock()
        return context

    @pytest.mark.asyncio
    async def test_your_async_function(self, mock_context):
        """Test your async function."""
        # Arrange
        expected_result = {"key": "value"}

        # Act
        result = await your_async_function(mock_context)

        # Assert
        assert result == expected_result

    def test_your_sync_function(self):
        """Test your synchronous function."""
        # Arrange
        input_data = "test_input"

        # Act
        result = your_sync_function(input_data)

        # Assert
        assert result is not None
```

### Testing with Mocks

```python
@patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.boto3')
def test_with_boto_mock(self, mock_boto3):
    """Test with mocked boto3."""
    # Setup mock
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client
    mock_client.list_workflows.return_value = {'workflows': []}

    # Test your function
    result = your_function_that_uses_boto3()

    # Verify
    mock_boto3.client.assert_called_with('omics')
    assert result == []
```

## MCP Tool Testing

### The Challenge

MCP tools use Pydantic `Field` annotations that are processed by the MCP framework. When testing directly, these annotations cause issues.

### The Solution: MCPToolTestWrapper

```python
from tests.test_helpers import MCPToolTestWrapper

class TestYourMCPTool:
    @pytest.fixture
    def tool_wrapper(self):
        return MCPToolTestWrapper(your_mcp_tool_function)

    @pytest.fixture
    def mock_context(self):
        context = AsyncMock()
        context.error = AsyncMock()
        return context

    @pytest.mark.asyncio
    async def test_mcp_tool(self, tool_wrapper, mock_context):
        """Test MCP tool using the wrapper."""
        # Mock dependencies
        with patch('your.dependency.module.SomeClass') as mock_class:
            mock_class.return_value.method.return_value = "expected"

            # Call using wrapper
            result = await tool_wrapper.call(
                ctx=mock_context,
                param1='value1',
                param2='value2',
            )

            # Validate
            assert result['key'] == 'expected_value'

    def test_tool_defaults(self, tool_wrapper):
        """Test that Field defaults are extracted correctly."""
        defaults = tool_wrapper.get_defaults()
        assert defaults['param_name'] == expected_default_value
```

### MCP Tool Testing Best Practices

1. **Always use MCPToolTestWrapper** for MCP tool functions
2. **Mock external dependencies** (AWS services, databases, etc.)
3. **Test both success and error scenarios**
4. **Validate response structure** and content
5. **Test default parameter handling**

## Test Utilities

### Core Utilities (`test_helpers.py`)

#### MCPToolTestWrapper

```python
wrapper = MCPToolTestWrapper(your_mcp_tool_function)

# Call with parameters
result = await wrapper.call(ctx=context, param1='value')

# Get default values
defaults = wrapper.get_defaults()
```

#### Direct Function Calling

```python
result = await call_mcp_tool_directly(
    tool_func=your_function,
    ctx=context,
    param1='value'
)
```

### Shared Fixtures (`conftest.py`)

```python
@pytest.fixture
def mock_context():
    """Mock MCP context."""
    context = AsyncMock()
    context.error = AsyncMock()
    return context

@pytest.fixture
def mock_aws_session():
    """Mock AWS session."""
    return MagicMock()
```

## Troubleshooting

### Common Issues

#### 1. FieldInfo Object Errors

**Error**: `AttributeError: 'FieldInfo' object has no attribute 'lower'`

**Solution**: Use `MCPToolTestWrapper` instead of calling MCP tools directly.

```python
# ❌ Don't do this
result = await search_genomics_files(ctx=context, file_type='bam')

# ✅ Do this instead
wrapper = MCPToolTestWrapper(search_genomics_files)
result = await wrapper.call(ctx=context, file_type='bam')
```

#### 2. Async Test Issues

**Error**: `RuntimeError: no running event loop`

**Solution**: Use `@pytest.mark.asyncio` decorator.

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await your_async_function()
    assert result is not None
```

#### 3. Import Errors

**Error**: `ModuleNotFoundError: No module named 'awslabs'`

**Solution**: Install in development mode.

```bash
pip install -e .
```

#### 4. Mock Issues

**Error**: Mocks not being applied correctly

**Solution**: Check patch paths and ensure they match the import paths in the code being tested.

```python
# ❌ Wrong path
@patch('boto3.client')

# ✅ Correct path (where it's imported)
@patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.boto3.client')
```

### Debug Mode

```bash
# Run with debug output
python -m pytest tests/ -v -s --log-cli-level=DEBUG

# Run single test with debugging
python -m pytest tests/test_file.py::test_method -v -s --pdb
```

## Best Practices

### Test Organization

1. **Group related tests** in classes
2. **Use descriptive test names** that explain what is being tested
3. **Follow the AAA pattern**: Arrange, Act, Assert
4. **Keep tests independent** - no test should depend on another

### Mocking Guidelines

1. **Mock external dependencies** (AWS services, databases, network calls)
2. **Don't mock the code you're testing**
3. **Use specific mocks** rather than generic ones
4. **Verify mock calls** when behavior is important

### Performance

1. **Keep unit tests fast** (< 1 second each)
2. **Use fixtures** for expensive setup
3. **Mock slow operations** (network calls, file I/O)
4. **Run tests in parallel** when possible

### Coverage

1. **Aim for high coverage** (80%+) but focus on quality
2. **Test edge cases** and error conditions
3. **Don't test trivial code** (simple getters/setters)
4. **Focus on business logic** and critical paths

### Documentation

1. **Write clear docstrings** for test methods
2. **Document complex test setups**
3. **Explain why tests exist**, not just what they do
4. **Keep documentation up to date**

## Test Execution Summary

Current test suite status:

```
✅ 532 Total Tests
✅ 100% Pass Rate
⏱️ ~7.5 seconds execution time
📊 57% Code Coverage
🔧 8 Integration Tests
🧪 500+ Unit Tests
```

### Test Categories Breakdown

- **Models & Validation**: 35 tests (100% pass)
- **Workflow Management**: 200+ tests (100% pass)
- **AWS Utilities**: 50+ tests (100% pass)
- **File Processing**: 100+ tests (100% pass)
- **Integration Tests**: 8 tests (100% pass)
- **Error Handling**: 50+ tests (100% pass)

## Contributing

When adding new tests:

1. **Follow naming conventions**: `test_*.py` for files, `test_*` for methods
2. **Add appropriate markers**: `@pytest.mark.asyncio` for async tests
3. **Include comprehensive assertions**
4. **Add docstrings** explaining test purpose
5. **Update this documentation** if adding new patterns or utilities

## Support

For questions about the testing framework:

1. Check this documentation first
2. Look at existing test examples
3. Review the `INTEGRATION_TEST_SOLUTION.md` for MCP-specific issues
4. Check the pytest documentation for general pytest questions
