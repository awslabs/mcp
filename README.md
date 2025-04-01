# AWS MCP Servers

A suite of specialized Model Context Protocol (MCP) servers that bring AWS expertise directly to your development workflow.

[![GitHub](https://img.shields.io/badge/github-awslabs/mcp-blue.svg?style=flat&logo=github)](https://github.com/awslabs/mcp)
[![License](https://img.shields.io/badge/license-Apache--2.0-brightgreen)](LICENSE)

## Available Servers

This monorepo contains the following MCP servers:

### MCP Bedrock Knowledge Bases Retrieval Expert

[![PyPI version](https://img.shields.io/pypi/v/awslabs.mcp-bedrock-kb-retrieval-expert.svg)](https://pypi.org/project/awslabs.mcp-bedrock-kb-retrieval-expert/)

A server for accessing Amazon Bedrock Knowledge Bases.

- Discover knowledge bases and their data sources
- Query knowledge bases with natural language
- Filter results by data source
- Rerank results

[Learn more](src/mcp-bedrock-kb-retrieval-expert/README.md) | [Documentation](https://awslabs.github.io/mcp/servers/mcp-bedrock-kb-retrieval-expert/)

### MCP CDK Expert

[![PyPI version](https://img.shields.io/pypi/v/awslabs.mcp-cdk-expert.svg)](https://pypi.org/project/awslabs.mcp-cdk-expert/)

A server for AWS CDK expertise and automation.

- AWS CDK project analysis and assistance
- CDK construct recommendations
- Infrastructure as Code best practices

[Learn more](src/mcp-cdk-expert/README.md) | [Documentation](https://awslabs.github.io/mcp/servers/mcp-cdk-expert/)

### MCP Cost Analysis Expert

[![PyPI version](https://img.shields.io/pypi/v/awslabs.mcp-cost-analysis-expert.svg)](https://pypi.org/project/awslabs.mcp-cost-analysis-expert/)

A server for AWS Cost Analysis.

- Analyze and visualize AWS costs
- Query cost data with natural language
- Generate cost reports and insights

[Learn more](src/mcp-cost-analysis-expert/README.md) | [Documentation](https://awslabs.github.io/mcp/servers/mcp-cost-analysis-expert/)

### MCP Nova Canvas Expert

[![PyPI version](https://img.shields.io/pypi/v/awslabs.mcp-nova-canvas-expert.svg)](https://pypi.org/project/awslabs.mcp-nova-canvas-expert/)

A server for generating images using Amazon Nova Canvas.

- Text-based image generation with customizable parameters
- Color-guided image generation with specific palettes
- Workspace integration for saving generated images
- AWS authentication through profiles

[Learn more](src/mcp-nova-canvas-expert/README.md) | [Documentation](https://awslabs.github.io/mcp/servers/mcp-nova-canvas-expert/)

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
    "mcp-nova-canvas-expert": {
      "command": "uvx",
      "args": ["awslabs.mcp-nova-canvas-expert@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    },
    "mcp-bedrock-kb-retrieval-expert": {
      "command": "uvx",
      "args": ["awslabs.mcp-bedrock-kb-retrieval-expert@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    },
    "mcp-cost-analysis-expert": {
      "command": "uvx",
      "args": ["awslabs.mcp-cost-analysis-expert@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    },
    "mcp-cdk-expert": {
      "command": "uvx",
      "args": ["awslabs.mcp-cdk-expert@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

See individual server READMEs for specific requirements and configuration options.

## Documentation

Comprehensive documentation for all servers is available on our [documentation website](https://awslabs.github.io/mcp/).

Documentation for each server:

- [MCP Bedrock Knowledge Bases Retrieval Expert](https://awslabs.github.io/mcp/servers/mcp-bedrock-kb-retrieval-expert/)
- [MCP Nova Canvas Expert](https://awslabs.github.io/mcp/servers/mcp-nova-canvas-expert/)

Documentation includes:

- Detailed guides for each server
- Installation and configuration instructions
- API references
- Usage examples

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.
