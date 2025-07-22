# AWS Elastic Beanstalk MCP Server

[![PyPI version](https://img.shields.io/pypi/v/awslabs.elastic-beanstalk-mcp-server.svg)](https://pypi.org/project/awslabs.elastic-beanstalk-mcp-server/)

A server for managing AWS Elastic Beanstalk environments and applications.

## Features

- Create and manage Elastic Beanstalk applications
- Deploy and update environments
- Monitor environment health and status
- View application versions and deployment history
- Manage configuration settings and environment properties
- Scale environments up or down
- Troubleshoot common Elastic Beanstalk issues

## Installation

```bash
pip install awslabs.elastic-beanstalk-mcp-server
```

Or using `uvx`:

```bash
uvx awslabs.elastic-beanstalk-mcp-server@latest
```

## Configuration

Add the following to your MCP client configuration:

```json
{
  "mcpServers": {
    "awslabs.elastic-beanstalk-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.elastic-beanstalk-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

## Usage

Once configured, your MCP client can use the Elastic Beanstalk MCP server to:

- Create and manage Elastic Beanstalk applications and environments
- Deploy applications to Elastic Beanstalk
- Monitor environment health and status
- Scale environments
- Troubleshoot issues

## Requirements

- Python 3.10+
- AWS credentials with appropriate permissions for Elastic Beanstalk
- An MCP client (such as Amazon Q, Cline, Cursor, or Windsurf)

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.