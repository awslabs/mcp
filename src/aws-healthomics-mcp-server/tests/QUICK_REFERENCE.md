# Testing Quick Reference

## Common Commands

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=awslabs.aws_healthomics_mcp_server --cov-report=html

# Run specific test file
python -m pytest tests/test_models.py -v

# Run integration tests only
python -m pytest tests/test_genomics_file_search_integration_working.py -v

# Run tests matching pattern
python -m pytest -k "workflow" tests/ -v

# Run failed tests only
python -m pytest --lf tests/
```

## Test File Patterns

| Pattern | Purpose | Example |
|---------|---------|---------|
| `test_*.py` | Unit tests | `test_models.py` |
| `test_*_integration_working.py` | Integration tests | `test_genomics_file_search_integration_working.py` |
| `test_workflow_*.py` | Workflow tests | `test_workflow_management.py` |
| `test_*_utils.py` | Utility tests | `test_aws_utils.py` |

## MCP Tool Testing Template

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from tests.test_helpers import MCPToolTestWrapper
from your.module import your_mcp_tool_function

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
    async def test_success_case(self, tool_wrapper, mock_context):
        with patch('your.dependency') as mock_dep:
            mock_dep.return_value = "expected"

            result = await tool_wrapper.call(
                ctx=mock_context,
                param1='value1'
            )

            assert result['key'] == 'expected'

    def test_defaults(self, tool_wrapper):
        defaults = tool_wrapper.get_defaults()
        assert defaults['param_name'] == expected_value
```


## Key Files

- `tests/test_helpers.py` - MCP tool testing utilities
- `tests/conftest.py` - Shared fixtures
- `tests/TESTING_FRAMEWORK.md` - Complete documentation
- `tests/INTEGRATION_TEST_SOLUTION.md` - MCP Field solution details
