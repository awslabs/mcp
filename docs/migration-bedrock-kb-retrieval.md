# Migration Guide: Bedrock KB Retrieval MCP Server to AWS Knowledge MCP Server

This guide helps you migrate from `awslabs.bedrock-kb-retrieval-mcp-server` to the [AWS Knowledge MCP Server](https://github.com/awslabs/mcp/tree/main/src/aws-knowledge-mcp-server).

## Why We're Deprecating

The AWS Knowledge MCP Server is a fully managed remote MCP server that provides up-to-date documentation, code samples, regional availability information, and other official AWS content. It offers broader knowledge retrieval capabilities without requiring local AWS credentials or infrastructure setup.

## Installing the Replacement

The AWS Knowledge MCP Server is a remote server -- no local installation required.

### Configuration

```json
{
  "mcpServers": {
    "aws-knowledge-mcp-server": {
      "url": "https://knowledge-mcp.global.api.aws",
      "type": "http",
      "disabled": false
    }
  }
}
```

If your client does not support HTTP transport, use the fastmcp proxy:

```json
{
  "mcpServers": {
    "aws-knowledge-mcp-server": {
      "command": "uvx",
      "args": ["fastmcp", "run", "https://knowledge-mcp.global.api.aws"]
    }
  }
}
```

### Key Differences

- **No AWS credentials required**: The Knowledge MCP Server does not require authentication (subject to rate limits)
- **No local setup**: No need to configure AWS_PROFILE, AWS_REGION, or boto3
- **Remote server**: Requires internet access; runs on AWS infrastructure

## Tool-by-Tool Migration

### ListKnowledgeBases -- No direct replacement

**Bedrock KB server:** Listed all Amazon Bedrock Knowledge Bases tagged with a configurable inclusion tag key, returning KB IDs, names, descriptions, and data sources.

**Knowledge server:** Does not discover or list Bedrock Knowledge Bases. The Knowledge server provides access to AWS documentation and official content, not user-provisioned knowledge bases.

**Alternative:** If you need to query your own Bedrock Knowledge Bases, use the AWS CLI:
```bash
aws bedrock-agent list-knowledge-bases
```

### QueryKnowledgeBases -- No direct replacement

**Bedrock KB server:** Queried a specific Bedrock Knowledge Base by ID with natural language, returning retrieved documents with relevance scores and source locations. Supported reranking and data source filtering.

**Knowledge server:** The `search_documentation` tool searches across all AWS documentation with natural language queries. However, it searches AWS official content, not your custom knowledge bases.

**Alternative:** If you need to query your own Bedrock Knowledge Bases, use the AWS CLI:
```bash
aws bedrock-agent-runtime retrieve --knowledge-base-id <id> --retrieval-query '{"text": "your query"}'
```

## New Capabilities in the Knowledge Server

The Knowledge server provides capabilities the Bedrock KB Retrieval server did not have:

| Tool | Description |
|------|-------------|
| `search_documentation` | Search across all AWS documentation with topic filtering |
| `read_documentation` | Retrieve and convert AWS doc pages to markdown |
| `recommend` | Get content recommendations for AWS documentation pages |
| `list_regions` | List all AWS regions with identifiers and names |
| `get_regional_availability` | Check service/feature availability by region |

### Knowledge Sources

The Knowledge server indexes content the Bedrock KB server could not access:
- AWS documentation and API references
- What's New posts and announcements
- Getting Started guides
- Builder Center content
- Blog posts and architectural references
- Well-Architected guidance
- Troubleshooting guides
- AWS Amplify documentation
- CDK and CloudFormation documentation

## Important: Different Use Cases

The two servers address fundamentally different use cases:

| | Bedrock KB Retrieval | AWS Knowledge |
|---|---|---|
| **Content source** | Your custom Bedrock Knowledge Bases | AWS official documentation |
| **Authentication** | AWS credentials required | No authentication needed |
| **Hosting** | Local (client-hosted) | Remote (AWS-managed) |
| **Customization** | Query your own data sources | AWS content only |
| **Reranking** | Supported (Amazon/Cohere models) | Not applicable |

If your primary use case is querying **your own custom knowledge bases**, the AWS Knowledge MCP Server is not a direct replacement. Consider using the AWS CLI or building a custom integration with the Bedrock Agent Runtime API.

If your use case is **accessing AWS documentation and official content**, the Knowledge server is a superior replacement with broader coverage and zero setup.

## Removing the Old Server

Once you've verified the replacement meets your needs:

1. Remove `awslabs.bedrock-kb-retrieval-mcp-server` from your MCP configuration
2. Uninstall the package: `pip uninstall awslabs.bedrock-kb-retrieval-mcp-server`
3. The old package will remain on PyPI but will not receive updates
