# Testing Quick Reference Guide

## Quick Commands

### Run All Tests
```bash
# Basic run
pytest tests/ -v

# With coverage
pytest tests/ --cov=src/datazone_mcp_server --cov-report=term-missing

# Fast failure (stop on first fail)
pytest tests/ -x

# Quiet mode
pytest tests/ -q
```

### Run Specific Tests
```bash
# Single test file
pytest tests/test_domain_management.py -v

# Single test class
pytest tests/test_domain_management.py::TestDomainRetrieval -v

# Single test function
pytest tests/test_domain_management.py::TestDomainRetrieval::test_get_domain_success -v

# Tests matching pattern
pytest tests/ -k "domain" -v
```

### Integration Tests
```bash
# Set up environment
export TEST_DATAZONE_DOMAIN_ID="your-domain-id"
export TEST_DATAZONE_PROJECT_ID="your-project-id"

# Run integration tests
pytest tests/test_integration.py -m integration -v

# Skip integration tests
export SKIP_AWS_TESTS=true
pytest tests/
```

### Coverage Reports
```bash
# HTML report
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html

# Missing lines report
pytest tests/ --cov=src --cov-report=term-missing

# Branch coverage
pytest tests/ --cov=src --cov-branch
```

## Test Structure Template

```python
"""
Test module for [functionality].
"""
import pytest
from unittest.mock import patch, Mock

class TestFeatureName:
    """Test cases for [specific feature]."""

    @pytest.mark.asyncio
    async def test_success_scenario(self, mcp_server_with_tools, tool_extractor):
        """Test [specific success scenario]."""
        # Arrange
        tool_function = tool_extractor(mcp_server_with_tools, 'tool_name')

        # Act
        result = await tool_function(param1="value1", param2="value2")

        # Assert
        assert result["key"] == "expected_value"

    @pytest.mark.asyncio
    async def test_error_scenario(self, mcp_server_with_tools, tool_extractor):
        """Test [specific error scenario]."""
        tool_function = tool_extractor(mcp_server_with_tools, 'tool_name')

        with pytest.raises(Exception) as exc_info:
            await tool_function(invalid_param="invalid")

        assert "expected error message" in str(exc_info.value)
```

## Common Patterns

### Mock AWS Client Response
```python
# In conftest.py or test file
mock_response = {
    "items": [{"id": "test-id", "name": "test-name"}],
    "nextToken": "token123"
}
mock_client.list_something.return_value = mock_response
```

### Test Parameter Validation
```python
@pytest.mark.asyncio
async def test_parameter_validation(self, mcp_server_with_tools, tool_extractor):
    """Test parameter validation."""
    tool_function = tool_extractor(mcp_server_with_tools, 'tool_name')

    with pytest.raises(Exception) as exc_info:
        await tool_function()  # Missing required parameter

    assert "required" in str(exc_info.value).lower()
```

### Test Pagination
```python
@pytest.mark.asyncio
async def test_pagination(self, mcp_server_with_tools, tool_extractor):
    """Test pagination handling."""
    tool_function = tool_extractor(mcp_server_with_tools, 'list_tool')

    result = await tool_function(max_results=10, next_token="token123")

    assert "items" in result
    assert isinstance(result["items"], list)
```

## Debugging

### Run with Debug Output
```bash
# Verbose output
pytest tests/test_file.py::test_function -vvs

# With Python debugger
pytest tests/test_file.py::test_function --pdb

# Show local variables on failure
pytest tests/test_file.py::test_function -l

# Capture print statements
pytest tests/test_file.py::test_function -s
```

### Common Issues

#### Import Errors
```bash
# Check if modules can be imported
python -c "from datazone_mcp_server import server; print('OK')"

# Check specific tool module
python -c "from datazone_mcp_server.tools import domain_management; print('OK')"
```

#### Async Test Issues
```python
# Correct: Use pytest.mark.asyncio
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()

# Incorrect: Missing asyncio marker
def test_async_function():  # Will fail
    result = await async_function()
```

#### Mock Issues
```python
# Correct: Patch the right path
@patch('datazone_mcp_server.tools.domain_management.datazone_client')

# Incorrect: Wrong patch path
@patch('boto3.client')  # Too broad, might not work
```

## Markers

### Available Markers
```bash
# Integration tests (require AWS)
pytest tests/ -m integration

# Slow tests
pytest tests/ -m slow

# Skip integration tests
pytest tests/ -m "not integration"
```

### Add Custom Markers
```python
# In test file
@pytest.mark.custom_marker
def test_function():
    pass

# In pyproject.toml
[tool.pytest.ini_options]
markers = [
    "custom_marker: description of marker",
]
```

## Coverage Targets

| Module | Current | Target |
|--------|---------|--------|
| Domain Management | 35% | 70% |
| Project Management | 70% | 80% |
| Data Management | 54% | 75% |
| Glossary | 90% | 95% |
| Environment | 55% | 75% |
| Server | 77% | 85% |

## Adding New Tests Checklist

- [ ] Test file follows naming convention: `test_<module>_<feature>.py`
- [ ] Uses `mcp_server_with_tools` and `tool_extractor` fixtures
- [ ] Includes both success and error scenarios
- [ ] Has proper docstrings explaining test purpose
- [ ] Uses `@pytest.mark.asyncio` for async tests
- [ ] Mocks external dependencies (AWS calls)
- [ ] Follows AAA pattern (Arrange-Act-Assert)
- [ ] Includes parameter validation tests
- [ ] Has meaningful assertions with clear error messages

## CI/CD Integration

```yaml
# Example GitHub Actions step
- name: Run Tests
  run: |
    pytest tests/ --cov=src --cov-report=xml --cov-fail-under=50

- name: Upload Coverage
  uses: codecov/codecov-action@v1
  with:
    file: ./coverage.xml
```

## Performance Guidelines

- Unit tests should complete in < 5 seconds total
- Individual tests should complete in < 100ms
- Integration tests can take up to 30 seconds per test
- Mock all external API calls to avoid network delays
- Use `pytest-xdist` for parallel execution if needed:
  ```bash
  pip install pytest-xdist
  pytest tests/ -n auto
  ```
