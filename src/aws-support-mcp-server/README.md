# AWS Support MCP Server

A Model Context Protocol (MCP) server implementation for interacting with the AWS Support API. This server enables AI assistants to create and manage AWS support cases programmatically.

## Features

- Create and manage AWS support cases
- Retrieve case information and communications
- Add communications to existing cases
- Resolve support cases
- Determine appropriate Issue Type, Service Code, and Category Code
- Determine appropriate Severity Level for a case


## Requirements

- Python 3.7+
- AWS credentials with Support API access
- Business, Enterprise On-Ramp, or Enterprise Support plan

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`

## Installation

Configure the MCP server in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`):

```json

{
   "mcpServers": {
      "awslabs_support_mcp_server": {
         "command": "uvx",
         "args": [
            "-m", "awslabs.aws-support-mcp-server@latest",
            "--debug",
            "--log-file",
            "./logs/mcp_support_server.log"
         ],
         "env": {
            "AWS_PROFILE": "your-aws-profile"
         }
      }
   }
}
```

Alternatively:
```bash


uv pip install -e .
uv run awslabs/aws_support_mcp_server/server.py
```

```json
{
   "mcpServers": {
      "awslabs_support_mcp_server": {
         "command": "path-to-python",
         "args": [
            "-m",
            "awslabs.aws_support_mcp_server.server",
            "--debug",
            "--log-file",
            "./logs/mcp_support_server.log"
         ],
         "env": {
            "AWS_PROFILE": "manual_enterprise"
         }
      }
   }
}
```

## Usage

Start the server:

```bash
python -m awslabs.aws_support_mcp_server.server [options]
```

Options:
- `--port PORT`: Port to run the server on (default: 8888)
- `--debug`: Enable debug logging
- `--log-file`: Where to save the log file

## Configuration

The server can be configured using environment variables:

- `AWS_REGION`: AWS region (default: us-east-1)
- `AWS_PROFILE`: AWS credentials profile name

## Documentation

For detailed documentation on available tools and resources, see the [API Documentation](docs/api.md).



## License

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License").
