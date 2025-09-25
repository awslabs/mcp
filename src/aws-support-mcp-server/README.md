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

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs_support_mcp_server&config=eyJjb21tYW5kIjoidXZ4IC1tIGF3c2xhYnMuYXdzLXN1cHBvcnQtbWNwLXNlcnZlckBsYXRlc3QgLS1kZWJ1ZyAtLWxvZy1maWxlIC4vbG9ncy9tY3Bfc3VwcG9ydF9zZXJ2ZXIubG9nIiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSJ9fQ%3D%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Support%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22-m%22%2C%22awslabs.aws-support-mcp-server%40latest%22%2C%22--debug%22%2C%22--log-file%22%2C%22.%2Flogs%2Fmcp_support_server.log%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%7D%7D) |

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

### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.aws-support-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.aws-support-mcp-server@latest",
        "awslabs.aws-support-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
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

For detailed documentation on available tools and resources, see the [API Documentation](https://github.com/awslabs/mcp/blob/main/src/aws-support-mcp-server/docs/api.md).



## License

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License").
