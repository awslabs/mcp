# AWS Labs aws-finops MCP Server

A Model Context Protocol (MCP) server that provides tools for AWS cost optimization by wrapping boto3 SDK functions.

## Introduction

The AWS FinOps MCP Server is designed to make AWS cost optimization recommendations and insights easily accessible to Large Language Models (LLMs) through the Model Context Protocol (MCP). It wraps boto3 SDK functions for AWS cost optimization services, allowing LLMs to directly interact with AWS cost optimization tools.

## Use case

This project enables LLMs to access AWS cost optimization services directly, allowing them to:

1. Retrieve cost optimization recommendations from AWS services
2. Analyze AWS resource usage and costs
3. Identify potential savings opportunities
4. Make data-driven recommendations for cost optimization

This helps AWS customers optimize their cloud spending by leveraging the analytical capabilities of LLMs combined with AWS's cost optimization services.

## Value proposition

The AWS FinOps MCP Server provides several key benefits:

1. **Simplified Access**: Makes AWS cost optimization services accessible to LLMs without complex integration
2. **Enhanced Analysis**: Combines AWS's cost data with LLM's analytical capabilities
3. **Actionable Insights**: Provides specific, actionable recommendations for cost savings
4. **Extensible Design**: Easily add support for additional AWS services and methods
5. **Standardized Interface**: Uses the Model Context Protocol for consistent interaction with different LLM platforms

## Project Structure

* `boto3_tools/`: Directory containing boto3 tool implementations
  * `boto3_docstrings.py`: Contains docstrings for all supported AWS services
  * `boto3_registry.py`: Implements the registry for boto3 tools
  * `__init__.py`: Package initialization
* `storage_lens/`: Directory containing Storage Lens query implementation
  * `manifest_handler.py`: Handles S3 manifest files
  * `athena_handler.py`: Manages Athena operations
  * `query_tool.py`: Main query tool implementation
* `prompts/`: Directory containing prompt templates for MCP clients
* `resources/`: Directory containing resource files and templates
* `server.py`: Implements the MCP server
* `__init__.py`: Makes the project a proper Python package
* `requirements.md`: Defines the requirements for this project
* `design.md`: Defines the design and architecture for this project
* `tests/`: Contains integration and unit tests for the server
  * `unit/`: Unit tests (no AWS API calls)
  * `integration/`: Integration tests (makes AWS API calls)
  * `unit/boto3_tools/`: Unit tests for boto3 tools
  * `unit/storage_lens/`: Unit tests for Storage Lens
  * `integration/boto3_tools/`: Integration tests for boto3 tools
  * `integration/storage_lens/`: Integration tests for Storage Lens

## Supported AWS Services

The server currently supports the following AWS services:

1. **Cost Optimization Hub**
   - get_recommendation
   - list_recommendations
   - list_recommendation_summaries

2. **Compute Optimizer**
   - get_auto_scaling_group_recommendations
   - get_ebs_volume_recommendations
   - get_ec2_instance_recommendations
   - get_ecs_service_recommendations
   - get_rds_database_recommendations
   - get_lambda_function_recommendations
   - get_idle_recommendations
   - get_effective_recommendation_preferences

3. **Cost Explorer**
   - get_reservation_purchase_recommendation
   - get_savings_plans_purchase_recommendation
   - get_cost_and_usage

4. **S3 Storage Lens**
   - storage_lens_run_query (custom implementation using Athena)

## Usage
To connect to your account using this MCP server, configure AWS credentials using standard AWS methods (environment variables, config files, IAM roles, etc.)

### Configuring the MCP Server

You can configure the MCP server using a JSON configuration file. This is particularly useful when integrating with MCP clients like Amazon Q, Claude Desktop, or other LLM applications.

Create a file named `mcp.json` with the following structure:

```json
{
  "mcpServers": {
    "aws-finops-mcp-server": {
      "autoApprove": [],
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/finops-mcp",
        "run",
        "server.py"
      ],
      "env": {
        "STORAGE_LENS_MANIFEST_LOCATION": "s3://your-bucket/StorageLens/account-id/configuration-id/"
      }
    }
  }
}
```

Configuration options:
- `autoApprove`: List of tools that don't require user approval before execution
- `disabled`: Whether the server is disabled
- `timeout`: Maximum execution time in seconds
- `type`: Transport type (stdio, http, etc.)
- `command`: Command to run the server
- `args`: Arguments for the command
- `env`: Environment variables for the server

Environment variables:
- `STORAGE_LENS_MANIFEST_LOCATION`: S3 location of Storage Lens manifest files
- `AWS_REGION`: AWS region to use

### Connecting to the server

You can connect to the server using any MCP client. For example, using the FastMCP client:

```python
from fastmcp import Client

async def main():
    client = Client("path/to/server.py")
    async with client:
        # Call a tool
        result = await client.call_tool("cost_explorer_get_cost_and_usage", {
            "params": {
                "TimePeriod": {
                    "Start": "2023-01-01",
                    "End": "2023-01-31"
                },
                "Granularity": "MONTHLY",
                "Metrics": ["BlendedCost"]
            }
        })
        print(result)

# Run the async function
import asyncio
asyncio.run(main())
```

## Testing

The project includes comprehensive tests for all components and AWS service integrations. To run the tests:

```bash

# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run only unit tests (no AWS API calls)
uv run pytest -m unit

# Run only integration tests (makes AWS API calls)
uv run pytest -m integration

# Run tests for a specific service
uv run pytest tests/integration/test_server.py

# Run with code coverage report
uv run pytest --cov=.
```

Note: Integration tests make actual AWS API calls and require valid AWS credentials. Tests will be skipped if you don't have the necessary permissions.

See the [tests/README.md](tests/README.md) file for more details on testing.
