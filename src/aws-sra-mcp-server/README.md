# AWS Security Reference Architecture MCP Server

The AWS SRA is a holistic set of guidelines for deploying the full complement of AWS security services in a multi-account environment. Use it to help design, implement, and manage AWS security services so that they align with AWS recommended practices. he recommendations are built around architecture that includes AWS security services—how they help achieve security objectives, where they can be best deployed and managed in your AWS accounts, and how they interact with other security services.

The SRA consists of content in both prescriptive guidance, CloudFormation and Terraform code examples, and assessment tooling to determine how compliant an AWS environment.

The AWS SRA MCP Server enables


## Overview

The AWS Security Reference Architecture MCP Server is a specialized MCP server that focuses on providing access to AWS security documentation, with an emphasis on the AWS Security Reference Architecture (SRA). It helps AI assistants provide accurate and up-to-date information about AWS security services, compliance frameworks, and security best practices.

## What is AWS Security Reference Architecture?

The AWS Security Reference Architecture (SRA) is a holistic set of guidelines for deploying the full complement of AWS security services in a multi-account environment. It provides prescriptive guidance on how to architect a security foundation across AWS accounts and AWS Organizations.

## Features

- **Security-focused documentation search**: Search AWS documentation with an emphasis on security and compliance content
- **Documentation reading**: Read and parse AWS security documentation pages
- **Related content recommendations**: Get recommendations for related security documentation

## Prerequisites

### Installation Requirements

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python 3.10 or newer using `uv python install 3.10` (or a more recent version)
3. **GitHub Token**: Create a GitHub personal access token for accessing AWS SRA repositories. Set
   the `GITHUB_TOKEN` environment variable with your token. For instructions on creating the
   personal access token, visit [GitHub's documentation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)

## Installation

|                                                                                                                                                                                                                   Cursor                                                                                                                                                                                                                    |                                                                                                                                                                                                                                                         VS Code                                                                                                                                                                                                                                                          |
| :-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: |
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/install-mcp?name=awslabs.aws-sra-mcp-server&config=%7B%22command%22%3A%20%22uvx%22%2C%22args%22%3A%20%5B%22awslabs.aws-sra-mcp-server%40latest%22%5D%2C%22env%22%3A%20%7B%20%22FASTMCP_LOG_LEVEL%22%3A%20%22ERROR%22%2C%20%22GITHUB_TOKEN%22%3A%20%22YOUR_TOKEN_HERE%22%7D%2C%22disabled%22%3A%20false%2C%22autoApprove%22%3A%20%5B%5D%7D%7D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20SRA%20MCP%20Server&config=%7B%22command%22%3A%20%22uvx%22%2C%22args%22%3A%20%5B%22awslabs.aws-sra-mcp-server%40latest%22%5D%2C%22env%22%3A%20%7B%20%22FASTMCP_LOG_LEVEL%22%3A%20%22ERROR%22%2C%20%22GITHUB_TOKEN%22%3A%20%22YOUR_TOKEN_HERE%22%7D%2C%22disabled%22%3A%20false%2C%22autoApprove%22%3A%20%5B%5D%7D%7D) |

### Amazon Q Developer CLI

Configure the MCP server in your Amazon Q Developer CLI configuration (edit `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.aws-sra-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-sra-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "GITHUB_TOKEN": "YOUR_TOKEN_HERE"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Cline

Configure the MCP server in your Cline MCP settings (`cline_mcp_settings.json`):

```json
{
  "mcpServers": {
    "awslabs.aws-sra-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-sra-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "GITHUB_TOKEN": "YOUR_TOKEN_HERE"
      }
    }
  }
}
```

### Kiro

Configure the MCP server in Kiro by navigating to `Kiro` > `MCP Servers` and adding to your Kiro MCP
Settings (`~/.kiro/setting/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.aws-sra-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-sra-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "GITHUB_TOKEN": "YOUR_TOKEN_HERE"
      }
    }
  }
}
```

### Docker

Or use docker after a successful `docker build -t mcp/aws-sra .`:

```json
{
  "mcpServers": {
    "awslabs.aws-sra-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "mcp/aws-sra:latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Basic Usage

Example:

- "Search for AWS security best practices for multi-account environments"
- "Show me documentation about AWS Security Reference Architecture for identity and access management"
- "What are the recommended security controls for AWS Organizations?"

## Tools

The server provides the following tools:

### search_content

Search AWS Security Reference Architecture documentation using the official AWS Documentation Search API.

```python
search_content(search_phrase: str, limit: int = 10) -> List[SearchResult]
```

### read_content

Fetch and convert an AWS Security Reference Architecture documentation page to markdown format.

```python
read_content(url: str, max_length: int = 5000, start_index: int = 0) -> str
```

### recommend

Get security content recommendations for an AWS Security Reference Architecture documentation page.

```python
recommend(url: str) -> List[RecommendationResult]
```

## License

This project is licensed under the Apache-2.0 License.
