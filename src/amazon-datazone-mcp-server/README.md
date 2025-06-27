# Amazon DataZone MCP Server

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-0.1.0-green.svg)](https://github.com/wangtianren/datazone-mcp-server/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-compatible-purple.svg)](https://modelcontextprotocol.io/)

A high-performance Model Context Protocol (MCP) server that provides seamless integration with Amazon DataZone services. This server enables AI assistants and applications to interact with Amazon DataZone APIs through a standardized interface.

## Features

- **Complete Amazon DataZone API Coverage**: Access all major DataZone operations
- **Modular Architecture**: Well-organized, maintainable code structure
- **Type Safety**: Full TypeScript-style type hints for Python
- **Comprehensive Error Handling**: Detailed error messages and proper exception handling
- **Production Ready**: Robust logging, validation, and configuration management

### Supported Operations

| Module | Operations |
|--------|------------|
| **Domain Management** | Create domains, manage domain units, search, policy grants |
| **Project Management** | Create/manage projects, project profiles, memberships |
| **Data Management** | Assets, listings, subscriptions, form types, data sources |
| **Glossary** | Business glossaries, glossary terms |
| **Environment** | Environments, connections, blueprints |

## Installation

### Prerequisites

- Python 3.10 or higher
- Install uv from [Astral](https://astral.sh/uv) or see the [GitHub README](https://github.com/astral-sh/uv#installation)
- AWS credentials configured
- An active Amazon DataZone domain

### Install from PyPI

```bash
pip install datazone-mcp-server
```

### Install from Source

```bash
git clone https://github.com/awslabs/amazon-datazone-mcp-server.git
cd datazone-mcp-server
pip install -e .
```

### Install with Cursor

[![Add to Cursor](https://img.shields.io/badge/Add%20to-Cursor-blue?style=for-the-badge&logo=cursor&logoColor=white)](cursor://anysphere.cursor-deeplink/mcp/install?name=amazon-datazone&config=eyJjb21tYW5kIjogInB5dGhvbjMiLCAiYXJncyI6IFsiLW0iLCAiYXdzbGFicy5kYXRhem9uZV9tY3Bfc2VydmVyLnNlcnZlciJdfQ==)

> Click the button above to instantly add the Amazon DataZone MCP server to your Cursor IDE. This will automatically configure the MCP server for use with Cursor's AI features.

**Prerequisites:**
- Python 3.10+ installed
- [uv](https://github.com/astral-sh/uv) installed - Get it from [Astral](https://astral.sh/uv) or see the [GitHub README](https://github.com/astral-sh/uv#installation)
- AWS credentials configured
- Install the package: `uvx awslabs.datazone-mcp-server@latest`

---

### Amazon Q CLI MCP Configuration

To enable this MCP server with **Amazon Q CLI**, configure the MCP endpoint by creating the file:

`~/.aws/amazonq/mcp.json`

```json
{
    "mcpServers": {
      "datazone": {
        "command": "uvx",
        "args": ["awslabs.datazone-mcp-server@latest"]
        "env": {
            "FASTMCP_LOG_LEVEL": "INFO"
        }
      }
   }
}

## Quick Start

### 1. Configure AWS Credentials

```bash
# Using AWS CLI
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

### 2. Start the MCP Server

```bash
python -m datazone_mcp_server.server
```

### 3. Use with an MCP Client

```python
import asyncio
from mcp import create_client

async def main():
    # Connect to the DataZone MCP server
    client = await create_client("stdio", ["python", "-m", "datazone_mcp_server.server"])

    # List available tools
    tools = await client.list_tools()
    print(f"Available tools: {len(tools.tools)}")

    # Call a DataZone operation
    result = await client.call_tool("get_domain", {
        "identifier": "dzd_your_domain_id"
    })
    print(result.content)

asyncio.run(main())
```

## Usage Examples

### Creating a DataZone Domain

```python
# Create a new DataZone domain
domain = await client.call_tool("create_domain", {
    "name": "MyDataDomain",
    "domain_execution_role": "arn:aws:iam::123456789012:role/DataZoneExecutionRole",
    "service_role": "arn:aws:iam::123456789012:role/DataZoneServiceRole",
    "description": "My data governance domain"
})
```

### Managing Projects

```python
# Create a project
project = await client.call_tool("create_project", {
    "domain_identifier": "dzd_abc123",
    "name": "Analytics Project",
    "description": "Project for analytics workloads"
})

# List projects
projects = await client.call_tool("list_projects", {
    "domain_identifier": "dzd_abc123"
})
```

### Working with Assets

```python
# Create an asset
asset = await client.call_tool("create_asset", {
    "domain_identifier": "dzd_abc123",
    "name": "Customer Data",
    "type_identifier": "amazon.datazone.RelationalTable",
    "owning_project_identifier": "prj_xyz789"
})

# Publish the asset
published = await client.call_tool("publish_asset", {
    "domain_identifier": "dzd_abc123",
    "asset_identifier": asset["id"]
})
```

## Architecture

```
datazone-mcp-server/
├── src/datazone_mcp_server/
│   ├── server.py              # Main MCP server entry point
│   ├── tools/                 # Tool modules
│   │   ├── common.py          # Shared utilities
│   │   ├── domain_management.py
│   │   ├── project_management.py
│   │   ├── data_management.py
│   │   ├── glossary.py
│   │   └── environment.py
│   └── __init__.py
├── tests/                     # Test suite
├── examples/                  # Usage examples
└── docs/                      # Documentation
```

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/awslabs/amazon-datazone-mcp-server.git
cd datazone-mcp-server

# Install with development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=datazone_mcp_server

# Run specific test file
pytest tests/test_domain_management.py
```

### Code Quality

```bash
# Format code
black src tests
isort src tests

# Type checking
mypy src

# Linting
flake8 src tests
```

## Available Tools

The Amazon DataZone MCP server provides **38 tools** organized into 5 categories:

### Domain Management
- `get_domain` - Retrieve domain information
- `create_domain` - Create a new domain
- `list_domain_units` - List domain units
- `create_domain_unit` - Create domain unit
- `list_domains` - List domains
- `add_entity_owner` - Add entity ownership
- `add_policy_grant` - Grant policies
- `search` - Search across DataZone
- `search_types` - Search typs across DataZone
- `get_user_profile` - Get user profile
- `search_user_profiles` - Search user profiles
- `search_group_profiles` - Search group profiles

### Project Management
- `create_project` - Create new project
- `get_project` - Get project details
- `list_projects` - List all projects
- `create_project_membership` - Add project members
- `list_project_profiles` - List project profiles
- `create_project_profile` - Create project profile
- `get_project_profile` - Get project profile
- `list_project_memberships` - List project memberships

### Glossary Management
- `create_glossary` - Create business glossary
- `create_glossary_term` - Create glossary term
- `get_glossary` - Get glossary details
- `get_glossary_term` - Get term details

### Data Management
- `get_asset` - Retrieve asset information
- `create_asset` - Create new asset
- `publish_asset` - Publish asset to catalog
- `get_listing` - Get asset listing
- `search_listings` - Search published assets
- `create_data_source` - Create data source
- `get_data_source` - Get data source
- `start_data_source_run` - Start data source run
- `create_subscription_request` - Request data subscription
- `accept_subscription_request` - Accept subscription
- `get_form_type` - Get metadata form type
- `create_form_type` - Create metadata form type
- `get_subscription` - Get subscription
- `list_data_sources` - List data sources


### Environment Management
- `list_environments` - List environments
- `create_connection` - Create environment connection
- `get_connection` - Get connection details
- `get_environment` - Get environment details
- `get_environment_blueprint` - Get environment blueprint
- `get_environment_blueprint_configuration` - Get environment blueprint configuration
- `list_connections` - List all connections
- `list_environment_blueprints` - List available blueprints
- `list_environment_blueprint_configurations` - List available blueprint configurations
- `list_environment_profiles` - List environment profiles

> **For detailed documentation** of each tool with parameters and examples, see our [Tool Reference](docs/TOOL_REFERENCE.md).

## Testing
To excute the tests, need to set up your `.env` file with arn credentials
```bash
export ARN=your_arn
export DOMAIN_EXECUTION_ROLE=your_domain_execution_role
export SERVICE_ROLERN=your_service_role
```


## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Disclaimer

**This is an unofficial, community-developed project and is not affiliated with, endorsed by, or supported by Amazon Web Services, Inc.**

- AWS and DataZone are trademarks of Amazon.com, Inc. or its affiliates
- This project provides a community-built interface to Amazon DataZone APIs
- Users are responsible for their own AWS credentials, costs, and compliance
- No warranty or support is provided - use at your own risk
- Always follow AWS security best practices when using this tool

For official Amazon DataZone documentation and support, visit [Amazon DataZone Documentation](https://docs.aws.amazon.com/datazone/).

## Support

- [Documentation](docs/)

## Acknowledgments

- [Model Context Protocol](https://modelcontextprotocol.io/) for the protocol specification
- [Amazon DataZone](https://aws.amazon.com/datazone/) for the data governance platform
- The open-source community for inspiration and contributions
