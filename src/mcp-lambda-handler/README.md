# mcp-lambda-handler

A serverless HTTP handler for the Model Context Protocol (MCP) using AWS Lambda. This package provides a flexible framework for building MCP HTTP endpoints with pluggable session management and AWS integration.

## Features
- Easy serverless MCP HTTP handler creation using AWS Lambda
- Pluggable session management system
- Built-in DynamoDB session backend support
- Customizable authentication and authorization
- Example implementations and tests

## Installation

> **Note:** This package is intended to be used as part of the [awslabs/mcp](https://github.com/awslabs/mcp) monorepo. For standalone development:
>
> ```bash
> pip install -e .[dev]
> ```

## Usage

```python
from awslabs.mcp_lambda_handler import MCPLambdaHandler

mcp = MCPLambdaHandler(name="mcp-lambda-server", version="1.0.0")

@mcp.tool()
def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

def lambda_handler(event, context):
    return mcp.handle_request(event, context)
```

## Development

- Install development dependencies:
  ```bash
  pip install -e .[dev]
  ```
- Run tests:
  ```bash
  pytest
  ```

## License

This project is licensed under the Apache-2.0 License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please see the [CONTRIBUTING.md](../../CONTRIBUTING.md) in the monorepo root for guidelines. 