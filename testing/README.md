# MCP Integration Testing Framework

This directory contains the integration testing framework for MCP servers in this repository.

## Overview

The testing framework provides utilities for:

- Automated testing of MCP servers using the [official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- Basic protocol validation
- Custom test execution
- Response validation using string patterns
- Pytest integration
- Type-safe test configuration with enums

## Structure

```
testing/
├── __init__.py                 # Package initialization
├── types.py                   # Type definitions and enums
├── mcp_test_client.py         # MCP client using official SDK
├── mcp_test_runner.py         # Test orchestration and execution
├── pytest_utils.py            # Pytest fixtures and utilities
├── requirements.txt           # Dependencies
└── README.md                 # This file
```

## Usage

### Basic Setup

The test framework uses the official MCP SDK. It will rely on it as a dependency in your server configuration.

Create integration tests for your MCP server in `src/<server-name>/tests/`

### Writing Tests

Create a test file following the naming convention `test_integ_<test_name>.py`:

```python
import pytest
from testing.pytest_utils import (
    MCPTestBase,
    create_test_config,
    create_tool_test_config,
    assert_test_results,
    TestType
)

class TestMyMCPServer:
    @pytest.fixture(autouse=True)
    def setup_test(self):
        self.test_instance = MCPTestBase(
            server_path="/path/to/server",
            command="uv",
            args=["run", "--frozen", "server.py"]
        )
        yield
        if self.test_instance:
            asyncio.run(self.test_instance.teardown())

    @pytest.mark.asyncio
    async def test_basic_protocol(self):
        expected_config = create_test_config(
            expected_tools={"count": 1, "names": ["my_tool"]},
            expected_resources={"count": 0},
            expected_prompts={"count": 0}
        )

        await self.test_instance.setup()
        results = await self.test_instance.run_basic_tests(expected_config)
        assert_test_results(results, expected_success_count=6)

    @pytest.mark.asyncio
    async def test_tool_call(self):
        await self.test_instance.setup()

        test_config = create_tool_test_config(
            tool_name="my_tool",
            arguments={"param": "value"},
            validation_rules=[
                {"type": "contains", "pattern": "expected_text", "field": "content"}
            ]
        )

        result = await self.test_instance.run_custom_test(test_config)
        assert result.success
```

### Running Tests

Run tests using pytest:

```bash
# Run all integration tests
pytest src/*/tests/test_integ_*.py -v -v

# Run tests for a specific server
pytest src/aws-documentation-mcp-server/tests/test_integ_*.py -v

# Run tests in parallel
pytest src/*/tests/test_integ_*.py -v -n 4
```

## Test Configuration

### Basic Protocol Tests

The framework automatically runs these basic tests:

- Connection establishment
- Ping test (via tools listing)
- Capabilities discovery
- Tools listing and validation
- Resources listing and validation
- Prompts listing and validation

### Helper Functions

The framework provides helper functions for creating test configurations:

#### `create_tool_test_config()`

Creates a tool call test configuration:

```python
test_config = create_tool_test_config(
    tool_name="my_tool",
    arguments={"param": "value"},
    validation_rules=[
        {"type": "contains", "pattern": "expected_text", "field": "content"}
    ],
    test_name="optional_test_name"
)
```

#### `create_resource_test_config()`

Creates a resource read test configuration:

```python
test_config = create_resource_test_config(
    uri="resource://example",
    validation_rules=[
        {"type": "contains", "pattern": "expected_content"}
    ]
)
```

#### `create_prompt_test_config()`

Creates a prompt get test configuration:

```python
test_config = create_prompt_test_config(
    prompt_name="my_prompt",
    arguments={"param": "value"},
    validation_rules=[
        {"type": "exact", "pattern": "expected_prompt"}
    ]
)
```

### Validation Types

- `exact`: Exact string match
- `contains`: Substring containment
- `regex`: Regular expression match

## Framework Components

### Types Module (`types.py`)

Contains type definitions and enums:

- `TestType` enum for test type safety
- Prevents circular imports between modules
- Centralized type definitions

### StdioMcpClient

Uses the official MCP Python SDK for communication:

- Process lifecycle management via `StdioServerParameters`
- Full MCP protocol implementation
- Tool, resource, and prompt operations using `ClientSession`

### MCPTestRunner

Orchestrates test execution:

- Test pipeline management
- Response validation
- Result collection and reporting

### MCPTestBase

Base class for integration tests:

- Setup and teardown management
- Test configuration
- Utility methods

## SDK Integration

The framework leverages the [official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) for:

- **Transport Management**: Uses `stdio_client` for stdio transport
- **Session Handling**: Uses `ClientSession` for protocol communication
- **Type Safety**: Uses official MCP types (`types.Tool`, `types.Resource`, etc.)
- **Protocol Compliance**: Ensures full MCP protocol compliance

### Client Instantiation

```python
from testing.mcp_test_client import StdioMcpClient

# Create stdio client
client = StdioMcpClient(
    command="uv",
    args=["run", "--frozen", "server.py"],
    env={"FASTMCP_LOG_LEVEL": "ERROR"}
)
```

## Architecture Notes

### Import Structure

```
types.py (base types)
    ↓
mcp_test_client.py (imports types)
    ↓
mcp_test_runner.py (imports types + client)
    ↓
pytest_utils.py (imports all above)
```

## Logging

The framework provides configurable logging:

- Default level: INFO
- Logs saved to `mcp_test.log`
- Server logs can be captured for debugging

## Troubleshooting

### Tests Hanging with Pytest

If tests hang when run with pytest, try:

1. Running tests directly with Python: `python integ/test_file.py`
2. Using different asyncio mode: `pytest --asyncio-mode=auto`
3. Checking for pytest configuration conflicts in server's `pyproject.toml`

### Import Errors

If you encounter import errors:

1. Ensure the testing framework path is correctly added to `sys.path`
2. Check that all dependencies are installed
3. Verify that the MCP SDK is available in the server's environment

## Future Enhancements

- **StreamableHttpMcpClient**: Support for HTTP transport
- Semantic validation using DeepEval framework
- AWS resource provisioning support
- Enhanced parallel execution
- Custom metrics and reporting
- Better pytest integration and configuration
