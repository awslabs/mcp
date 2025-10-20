# ECS MCP Server Integration Tests

This directory contains integration tests for the ECS MCP Server using the MCP Inspector CLI tool. These tests provide a more realistic testing environment by interacting with the MCP server through the same interface that MCP clients would use.

## Framework Overview

The integration test framework consists of:

- **`mcp_inspector_framework.py`**: Core framework for running MCP inspector commands
- **`test_ecs_mcp_inspector.py`**: Actual integration tests for the ECS MCP server
- **`conftest.py`**: Pytest configuration and fixtures
- **`run_tests.py`**: Standalone test runner for development

## Prerequisites

1. **Node.js and npm**: Required for the MCP inspector CLI tool
2. **uv**: Python package manager (should be installed at `/opt/homebrew/bin/uv`)
3. **MCP Inspector**: Installed automatically via npx

## Running Tests

### Using pytest (Recommended)

```bash
# Run all integration tests
cd /Users/mtgoo/dev/ecs-mcp-server/mcp/src/ecs-mcp-server
python -m pytest tests/integ_tests/ -v

# Run specific test
python -m pytest tests/integ_tests/test_ecs_mcp_inspector.py::TestECSMCPInspector::test_list_tools_basic -v

# Run with detailed logging
python -m pytest tests/integ_tests/ -v -s --log-cli-level=INFO
```

### Using the standalone runner

```bash
cd /Users/mtgoo/dev/ecs-mcp-server/mcp/src/ecs-mcp-server
python tests/integ_tests/run_tests.py
```

### Quick single test

```bash
cd /Users/mtgoo/dev/ecs-mcp-server/mcp/src/ecs-mcp-server
python -c "from tests.integ_tests.test_ecs_mcp_inspector import test_ecs_mcp_tools_list; test_ecs_mcp_tools_list()"
```

## Test Categories

### Basic Tests
- **`test_list_tools_basic`**: Tests the basic `tools/list` functionality
- **`test_server_startup_time`**: Ensures server starts within reasonable time
- **`test_invalid_method_handling`**: Tests error handling for invalid methods

### Tool Validation Tests
- **`test_expected_ecs_tools_exist`**: Verifies expected ECS tools are present
- **`test_tools_have_descriptions`**: Ensures all tools have meaningful descriptions

### Advanced Tests
- **`test_tool_call_example`**: Example of calling specific tools (currently skipped)
- **`test_resources_list`**: Tests resource listing if supported

## Framework Features

### MCPInspectorFramework Class
- Wraps the MCP inspector CLI tool
- Handles command execution and result parsing
- Provides convenient methods for common operations:
  - `list_tools()`: List all available tools
  - `call_tool(name, args)`: Call a specific tool
  - `list_resources()`: List available resources
  - `get_resource(uri)`: Get specific resource

### MCPTestAssertions Class
- Custom assertions for MCP-specific validations:
  - `assert_tools_exist()`: Verify specific tools exist
  - `assert_tool_has_schema()`: Verify tool has proper input schema
  - `assert_execution_time_under()`: Performance assertions
  - `assert_tool_call_success()`: Verify successful tool execution

### MCPInspectorResult Class
- Structured result from inspector commands
- Includes parsed JSON, execution time, and error details

## Adding New Tests

### 1. Basic Tool Test
```python
def test_my_new_tool(self):
    """Test a specific tool."""
    result = self.framework.list_tools()
    self.assertions.assert_tools_exist(result, ["my_tool_name"])
```

### 2. Tool Call Test
```python
def test_call_my_tool(self):
    """Test calling a specific tool."""
    result = self.framework.call_tool("my_tool", {"param": "value"})
    self.assertions.assert_tool_call_success(result, "my_tool")
```

### 3. Performance Test
```python
def test_tool_performance(self):
    """Test tool performance."""
    result = self.framework.list_tools()
    self.assertions.assert_execution_time_under(result, 2.0)  # 2 seconds
```

## Configuration

### Environment Variables
- `UV_PATH`: Override the path to the uv binary
- `MCP_INSPECTOR_TIMEOUT`: Override the default timeout (30 seconds)

### Test Markers
- `@pytest.mark.slow`: For tests that take more than 5 seconds
- `@pytest.mark.requires_aws`: For tests requiring AWS credentials
- `@pytest.mark.requires_docker`: For tests requiring Docker
- `@pytest.mark.tool_call`: For tests that call MCP tools

## Troubleshooting

### Common Issues

1. **"npx command not found"**
   - Install Node.js and npm
   - Ensure npx is in your PATH

2. **"uv command not found"**
   - Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Update the `uv_path` in the framework initialization

3. **"Server path does not exist"**
   - Verify the path to `main.py` is correct
   - Check that the ECS MCP server is properly installed

4. **Timeout errors**
   - Increase the timeout in framework initialization
   - Check if the server is hanging during startup

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Manual Inspector Command

Test the inspector command manually:
```bash
npx @modelcontextprotocol/inspector --cli --method tools/list -- /opt/homebrew/bin/uv --directory /Users/mtgoo/dev/ecs-mcp-server/mcp/src/ecs-mcp-server/awslabs/ecs_mcp_server run main.py
```

## Extending the Framework

The framework is designed to be extensible for testing other MCP servers:

```python
# Test a different MCP server
framework = MCPInspectorFramework(
    server_path="/path/to/other/server/main.py",
    server_args=["--custom-arg", "value"],
    timeout=60
)
```

## Future Enhancements

- Support for testing MCP servers with different transport protocols
- Parallel test execution
- Test result reporting and metrics
- Integration with CI/CD pipelines
- Mock AWS services for testing without real AWS resources
