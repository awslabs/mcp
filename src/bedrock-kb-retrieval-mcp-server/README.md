# Amazon Bedrock Knowledge Base Retrieval MCP Server

MCP server for accessing Amazon Bedrock Knowledge Bases

## Features

### Discover knowledge bases and their data sources

- Find and explore all available knowledge bases
- Search for knowledge bases by name or tag
- List data sources associated with each knowledge base

### Query knowledge bases with natural language

- Retrieve information using conversational queries
- Get relevant passages from your knowledge bases
- Access citation information for all results

### Filter results by data source

- Focus your queries on specific data sources
- Include or exclude specific data sources
- Prioritize results from specific data sources

### Rerank results

- Improve relevance of retrieval results
- Use Amazon Bedrock reranking capabilities
- Sort results by relevance to your query

## Prerequisites

### Installation Requirements

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`

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
3. Reranking is only available in specific regions. Please refer to the official [documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/rerank-supported.html) for an up to date list of supported regions.
4. Enable model access for the available reranking models in the specified region.

### Controlling Reranking

Reranking can be globally enabled or disabled using the `BEDROCK_KB_RERANKING_ENABLED` environment variable:

- Set to `false` (default): Disables reranking for all queries unless explicitly enabled
- Set to `true`: Enables reranking for all queries unless explicitly disabled

The environment variable accepts various formats:

- For enabling: 'true', '1', 'yes', or 'on' (case-insensitive)
- For disabling: any other value or not set (default behavior)

This setting provides a global default, while individual API calls can still override it by explicitly setting the `reranking` parameter.

For detailed instructions on setting up knowledge bases, see:

- [Create a knowledge base](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-create.html)
- [Managing permissions for Amazon Bedrock knowledge bases](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-prereq-permissions-general.html)
- [Permissions for reranking in Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/rerank-prereq.html)

## Installation

Here are some ways you can work with MCP across AWS, and we'll be adding support to more products including Amazon Q Developer CLI soon: (e.g. for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.bedrock-kb-retrieval-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.bedrock-kb-retrieval-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-profile-name",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR",
        "KB_INCLUSION_TAG_KEY": "optional-tag-key-to-filter-kbs",
        "BEDROCK_KB_RERANKING_ENABLED": "false"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

or docker after a succesful `docker build -t awslabs/bedrock-kb-retrieval-mcp-server .`:

```file
# ficticious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_SESSION_TOKEN=AQoEXAMPLEH4aoAH0gNCAPy...truncated...zrkuWJOgQs8IZZaIv2BXIa2R4Olgk
```

```json
  {
    "mcpServers": {
      "awslabs.bedrock-kb-retrieval-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "--env",
          "FASTMCP_LOG_LEVEL=ERROR",
          "--env",
          "KB_INCLUSION_TAG_KEY=optional-tag-key-to-filter-kbs",
          "--env",
          "BEDROCK_KB_RERANKING_ENABLED=false",
          "--env",
          "AWS_REGION=us-east-1",
          "--env-file",
          "/full/path/to/file/above/.env",
          "awslabs/bedrock-kb-retrieval-mcp-server:latest"
        ],
        "env": {},
        "disabled": false,
        "autoApprove": []
      }
    }
  }
```

NOTE: Your credentials will need to be kept refreshed from your host

## Limitations

- Results with `IMAGE` content type are not included in the KB query response.
- The `reranking` parameter requires additional permissions, Amazon Bedrock model access, and is only available in specific regions.


## Resources 

### Open MCP Marketplace API Support
<details>
<summary><b>Open MCP Marketplace API Support</b></summary>

![MCP Marketplace User Review Rating Badge](http://www.deepnlp.org/api/marketplace/svg?awslabs/mcp)|[Reviews](http://www.deepnlp.org/store/ai-agent/mcp-server/pub-awslabs/mcp)|[GitHub](https://github.com/AI-Agent-Hub/mcp-marketplace)|[Doc](http://www.deepnlp.org/doc/mcp_marketplace)|[MCP Marketplace](http://www.deepnlp.org/store/ai-agent/mcp-server)

Allow AI/Agent/LLM to find this MCP Server via common python/typescript API, search and explore relevant servers and tools

***Example: Search Server and Tools***
```python
import anthropic
import mcp_marketplace as mcpm

result_q = mcpm.search(query="mcp", mode="list", page_id=0, count_per_page=100, config_name="deepnlp") # search server by category choose various endpoint
result_id = mcpm.search(id="awslabs/mcp", mode="list", page_id=0, count_per_page=100, config_name="deepnlp")      # search server by id choose various endpoint 
tools = mcpm.list_tools(id="awslabs/mcp", config_name="deepnlp_tool")
# Call Claude to Choose Tools Function Calls 
# client = anthropic.Anthropic()
# response = client.messages.create(model="claude-opus-4-20250514", max_tokens=1024, tools=tools, messages=[])
```

</details>


