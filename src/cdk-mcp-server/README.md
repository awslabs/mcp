# CDK MCP Server

MCP server for AWS Cloud Development Kit (CDK) best practices, infrastructure as code patterns, and security compliance with CDK Nag.

## Features

### Tools

- **CDKGeneralGuidance** - Get prescriptive CDK advice for building applications on AWS
- **ExplainCDKNagRule** - Explain specific CDK Nag rules with AWS Well-Architected guidance
- **CheckCDKNagSuppressions** - Check if CDK code contains Nag suppressions that require human review
- **GenerateBedrockAgentSchemaFromFile** - Generate OpenAPI schema for Bedrock Agent Action Groups from a file
- **GetAwsSolutionsConstructPattern** - Search and discover AWS Solutions Constructs patterns
- **SearchGenAICDKConstructs** - Search for GenAI CDK constructs by name or type

### Resources

- **CDK Nag Rules** - Access rule packs via `cdk-nag://rules/{rule_pack}`
- **Lambda Powertools** - Get guidance on Lambda Powertools via `lambda-powertools://{topic}`
- **AWS Solutions Constructs** - Access patterns via `aws-solutions-constructs://{pattern_name}`
- **GenAI CDK Constructs** - Access documentation via `genai-cdk-constructs://{construct_type}/{construct_name}`

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.13`

## Installation

Add the server to your MCP client config (e.g. for Amazon Q CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.cdk-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.cdk-mcp-server@latest"],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Security Considerations

When using this MCP server, you should consider:

- Reviewing all CDK Nag warnings and errors manually
- Fixing security issues rather than suppressing them whenever possible
- Documenting clear justifications for any necessary suppressions
- Using the CheckCDKNagSuppressions tool to verify no unauthorized suppressions exist

Before applying CDK NAG Suppressions, you should consider conducting your own independent assessment to ensure that your use would comply with your own specific security and quality control practices and standards, as well as the local laws, rules, and regulations that govern you and your content.
