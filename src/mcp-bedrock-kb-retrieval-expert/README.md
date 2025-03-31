# awslabs MCP Bedrock KB Retrieval Expert

A Model Context Protocol (MCP) server for accessing Amazon Bedrock Knowledge Bases.

## Features

- Discover knowledge bases and their data sources
- Query knowledge bases with natural language
- Filter results by data source
- Rerank results

## Prerequisites

### Installation Requirements

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.13`

### AWS Requirements

1. **AWS CLI Configuration**: You must have the AWS CLI configured with credentials and an AWS_PROFILE that has access to Amazon Bedrock and Knowledge Bases
2. **Amazon Bedrock Knowledge Base**: You must have at least one Amazon Bedrock Knowledge Base with the tag key `mcp-multirag-kb` with a value of `true`
3. **IAM Permissions**: Your IAM role/user must have appropriate permissions to:
   - List and describe knowledge bases
   - Access data sources
   - Query knowledge bases

### Reranking Requirements

If you intend to use reranking functionality, your Bedrock Knowledge Base needs additional permissions:

1. Your IAM role must have permissions for both `bedrock:Rerank` and `bedrock:InvokeModel` actions
2. The Amazon Bedrock Knowledge Bases service role must also have these permissions
3. Reranking is only available in specific regions: us-west-2, us-east-1, ap-northeast-1, and ca-central-1

For detailed instructions on setting up knowledge bases, see:

- [Create a knowledge base](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-create.html)
- [Managing permissions for Amazon Bedrock knowledge bases](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-prereq-permissions-general.html)
- [Permissions for reranking in Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/rerank-prereq.html)

## Installation

Add the server to your MCP client config (e.g. for Amazon Q CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.mcp-bedrock-kb-retrieval-expert": {
      "command": "uvx",
      "args": ["awslabs.mcp-bedrock-kb-retrieval-expert"],
      "env": {
        "SHELL": "/usr/bin/zsh",
        "AWS_PROFILE": "your-profile-name"
      }
    }
  }
}
```

## Limitations

- Results with `IMAGE` content type are not included in the KB query response.
- The `reranking` parameter requires additional permissions, Amazon Bedrock model access, and is only available in specific regions.
