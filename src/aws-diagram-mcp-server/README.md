# AWS Diagram MCP Server

An MCP server that seamlessly creates diagrams using the Python diagrams package DSL. This server allows you to generate AWS diagrams, sequence diagrams, flow diagrams, and class diagrams using Python code.

[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/)

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Install GraphViz https://www.graphviz.org/

## Installation

Install the MCP server:
```bash
uv tool install aws-diagram-mcp-server-mcp-server
```

Add the server to your MCP client config (e.g. `~/.cursor-server/data/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`):
```json
{
  "mcpServers": {
    "aws-diagram-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-diagram-mcp-server-mcp-server"],
      "env": {
        "SHELL": "/usr/bin/zsh"
      }
    }
  }
}
```

## Features

The Diagrams MCP Server provides the following capabilities:

1. **Generate Diagrams**: Create professional diagrams using Python code
2. **Multiple Diagram Types**: Support for AWS architecture, sequence diagrams, flow charts, class diagrams, and more
3. **Customization**: Customize diagram appearance, layout, and styling
4. **Security**: Code scanning to ensure secure diagram generation

## Quick Start Example

The repository includes an example script (`example_diagram.py`) that demonstrates how to create a simple AWS architecture diagram:

```python
from diagrams import Diagram
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.aws.network import ELB

# Create a simple AWS diagram
with Diagram('Web Service Architecture', show=True, outformat='png', filename='example_diagram'):
    ELB('lb') >> EC2('web') >> RDS('userdb')
```

Running this script will generate an `example_diagram.png` file that visualizes a basic web service architecture with a load balancer, web server, and database:

```bash
python example_diagram.py
```

The generated diagram shows the flow from the Elastic Load Balancer (ELB) to an EC2 instance, and then to an RDS database, representing a typical three-tier web architecture.

## Development

### Testing

The project includes a comprehensive test suite to ensure the functionality of the MCP server. The tests are organized by module and cover all aspects of the server's functionality.

To run the tests, use the provided script:

```bash
./run_tests.sh
```

This script will automatically install pytest and its dependencies if they're not already installed.

Or run pytest directly (if you have pytest installed):

```bash
pytest -xvs tests/
```

To run with coverage:

```bash
pytest --cov=awslabs.aws_diagram_mcp_server --cov-report=term-missing tests/
```

For more information about the tests, see the [tests README](tests/README.md).

### Development Dependencies

To set up the development environment, install the development dependencies:

```bash
uv pip install -e ".[dev]"
```

This will install the required dependencies for development, including pytest, pytest-asyncio, and pytest-cov.
