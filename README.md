# AWS MCP Servers

A suite of specialized MCP servers that bring AWS best practices directly to your development workflow.

[![GitHub](https://img.shields.io/badge/github-awslabs/mcp-blue.svg?style=flat&logo=github)](https://github.com/awslabs/mcp)
[![License](https://img.shields.io/badge/license-Apache--2.0-brightgreen)](LICENSE)

## Available Servers

This monorepo contains the following MCP servers:

### Core MCP Server

[![PyPI version](https://img.shields.io/pypi/v/awslabs.core-mcp-server.svg)](https://pypi.org/project/awslabs.core-mcp-server/)

A server for managing and coordinating other AWS Labs MCP servers.

- Automatic MCP Server Management
- Planning and guidance to orchestrate AWS Labs MCP Servers
- UVX Installation Support
- Centralized Configuration

[Learn more](src/core-mcp-server/README.md) | [Documentation](https://awslabs.github.io/mcp/servers/core-mcp-server/)

### Bedrock Knowledge Bases Retrieval MCP Server

[![PyPI version](https://img.shields.io/pypi/v/awslabs.bedrock-kb-retrieval-mcp-server.svg)](https://pypi.org/project/awslabs.bedrock-kb-retrieval-mcp-server/)

A server for accessing Amazon Bedrock Knowledge Bases.

- Discover knowledge bases and their data sources
- Query knowledge bases with natural language
- Filter results by data source
- Rerank results

[Learn more](src/bedrock-kb-retrieval-mcp-server/README.md) | [Documentation](https://awslabs.github.io/mcp/servers/bedrock-kb-retrieval-mcp-server/)

### CDK MCP Server

[![PyPI version](https://img.shields.io/pypi/v/awslabs.cdk-mcp-server.svg)](https://pypi.org/project/awslabs.cdk-mcp-server/)

A server for AWS CDK best practices.

- AWS CDK project analysis and assistance
- CDK construct recommendations
- Infrastructure as Code best practices

[Learn more](src/cdk-mcp-server/README.md) | [Documentation](https://awslabs.github.io/mcp/servers/cdk-mcp-server/)

### Cost Analysis MCP Server

[![PyPI version](https://img.shields.io/pypi/v/awslabs.cost-analysis-mcp-server.svg)](https://pypi.org/project/awslabs.cost-analysis-mcp-server/)

A server for AWS Cost Analysis.

- Analyze and visualize AWS costs
- Query cost data with natural language
- Generate cost reports and insights

[Learn more](src/cost-analysis-mcp-server/README.md) | [Documentation](https://awslabs.github.io/mcp/servers/cost-analysis-mcp-server/)

### Nova Canvas MCP Server

[![PyPI version](https://img.shields.io/pypi/v/awslabs.nova-canvas-mcp-server.svg)](https://pypi.org/project/awslabs.nova-canvas-mcp-server/)

A server for generating images using Amazon Nova Canvas.

- Text-based image generation with customizable parameters
- Color-guided image generation with specific palettes
- Workspace integration for saving generated images
- AWS authentication through profiles

[Learn more](src/nova-canvas-mcp-server/README.md) | [Documentation](https://awslabs.github.io/mcp/servers/nova-canvas-mcp-server/)

## Installation and Setup

Each server has specific installation instructions. Generally, you can:

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/)
2. Install Python using `uv python install 3.13`
3. Configure AWS credentials with access to required services
4. Add the server to your MCP client configuration

Example configuration for Amazon Q CLI MCP (`~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.core-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.core-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.nova-canvas-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.nova-canvas-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.bedrock-kb-retrieval-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.bedrock-kb-retrieval-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.cost-analysis-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.cost-analysis-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.cdk-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.cdk-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
    }
  }
}
```

See individual server READMEs for specific requirements and configuration options.

## Documentation

Comprehensive documentation for all servers is available on our [documentation website](https://awslabs.github.io/mcp/).

Documentation for each server:

- [Bedrock Knowledge Bases Retrieval MCP Server](https://awslabs.github.io/mcp/servers/bedrock-kb-retrieval-mcp-server/)
- [Nova Canvas MCP Server](https://awslabs.github.io/mcp/servers/nova-canvas-mcp-server/)
- [Cost Analysis MCP Server](https://awslabs.github.io/mcp/servers/cost-analysis-mcp-server/)
- [CDK MCP Server](https://awslabs.github.io/mcp/servers/cdk-mcp-server/)

Documentation includes:

- Detailed guides for each server
- Installation and configuration instructions
- API references
- Usage examples

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.

## Disclaimer

Before using an MCP Server, you should consider conducting your own independent assessment to ensure that your use would comply with your own specific security and quality control practices and standards, as well as the laws, rules, and regulations that govern you and your content.
