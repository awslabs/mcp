# Amazon Bedrock Knowledge Base Retrieval MCP Server

MCP server for accessing Amazon Bedrock Knowledge Bases

## Features

| Feature | Description |
|---------|-------------|
| **Knowledge Base Discovery** | Find and explore all available knowledge bases, search by name or tag, and list associated data sources |
| **Natural Language Queries** | Retrieve information using conversational queries with relevant passages and citation information |
| **Data Source Filtering** | Focus queries on specific data sources, include/exclude sources, or prioritize results from specific sources |
| **Result Reranking** | Improve relevance of retrieval results using Amazon Bedrock reranking capabilities |
| **Single KB Mode** | Configure the server to work exclusively with one knowledge base using environment variables |

## Prerequisites

### 🔧 Installation Requirements

- **uv**: Install from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
- **Python 3.10**: Install using `uv python install 3.10`

### ☁️ AWS Requirements

- **AWS CLI Configuration**: Configure with credentials and an AWS_PROFILE that has access to Amazon Bedrock and Knowledge Bases
- **Amazon Bedrock Knowledge Base**: At least one Knowledge Base with the tag key `mcp-multirag-kb` set to `true`
- **IAM Permissions**: Required permissions include:
  - List and describe knowledge bases
  - Access data sources
  - Query knowledge bases

### 🔄 Reranking Requirements

For reranking functionality, additional setup is required:

- **IAM Permissions**: Both your IAM role and the Amazon Bedrock Knowledge Bases service role need:
  - `bedrock:Rerank`
  - `bedrock:InvokeModel`
- **Regional Availability**: Reranking is only available in specific regions ([documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/rerank-supported.html))
- **Model Access**: Enable access for reranking models in your region

### 📚 Additional Resources

- [Create a knowledge base](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-create.html)
- [Managing permissions for Amazon Bedrock knowledge bases](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-prereq-permissions-general.html)
- [Permissions for reranking in Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/rerank-prereq.html)

## Configuration

### Environment Variables

The MCP server supports the following environment variables:

| Variable | Description | Default | Example |
|----------|-------------|---------|----------|
| `AWS_PROFILE` | AWS profile to use | - | `"your-profile-name"` |
| `AWS_REGION` | AWS region | - | `"us-east-1"` |
| `FASTMCP_LOG_LEVEL` | Logging level | - | `"ERROR"` |
| `KB_INCLUSION_TAG_KEY` | Tag key to filter knowledge bases | `"mcp-multirag-kb"` | `"custom-tag-key"` |
| `BEDROCK_KB_RERANKING_ENABLED` | Enable/disable reranking globally | `false` | `"true"`, `"false"`, `"1"`, `"yes"`, `"on"` |
| `BEDROCK_KB_ID` | Override knowledge base ID for all queries | - | `"EXAMPLEKBID"` |
| `BEDROCK_KB_FORCE_OVERRIDE` | Force use of `BEDROCK_KB_ID` regardless of query parameters | `false` | `"true"` |

### Single Knowledge Base Mode

To configure the server to work with a single knowledge base:

1. **Set the knowledge base ID**: Use `BEDROCK_KB_ID` to specify which knowledge base to use
2. **Optional - Force override**: Set `BEDROCK_KB_FORCE_OVERRIDE=true` to ignore all query parameters and always use the specified knowledge base


```bash
# Example: Always use a specific knowledge base
export BEDROCK_KB_ID="EXAMPLEKBID"
export BEDROCK_KB_FORCE_OVERRIDE="true"
```


When force override is enabled, the server will ignore the `knowledgeBaseId` parameter in all queries and use the specified `BEDROCK_KB_ID` instead.

## Installation

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/install-mcp?name=awslabs.bedrock-kb-retrieval-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYmVkcm9jay1rYi1yZXRyaWV2YWwtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJ5b3VyLXByb2ZpbGUtbmFtZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEiLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIiwiS0JfSU5DTFVTSU9OX1RBR19LRVkiOiJvcHRpb25hbC10YWcta2V5LXRvLWZpbHRlci1rYnMiLCJCRURST0NLX0tCX1JFUkFOS0lOR19FTkFCTEVEIjoiZmFsc2UifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119)

Configure the MCP server in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`):

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
        "BEDROCK_KB_RERANKING_ENABLED": "false",
        "BEDROCK_KB_ID": "",
        "BEDROCK_KB_FORCE_OVERRIDE": "false"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Docker Installation

After building the Docker image with `docker build -t awslabs/bedrock-kb-retrieval-mcp-server .`:

1. **Create an environment file** (`.env`):

   ```bash
   # Example .env file with AWS temporary credentials
   AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
   AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
   AWS_SESSION_TOKEN=AQoEXAMPLEH4aoAH0gNCAPy...truncated...zrkuWJOgQs8IZZaIv2BXIa2R4Olgk
   ```

2. **Configure MCP client**:

   ```json
   {
     "mcpServers": {
       "awslabs.bedrock-kb-retrieval-mcp-server": {
         "command": "docker",
         "args": [
           "run",
           "--rm",
           "--interactive",
           "--env", "FASTMCP_LOG_LEVEL=ERROR",
           "--env", "KB_INCLUSION_TAG_KEY=optional-tag-key-to-filter-kbs",
           "--env", "BEDROCK_KB_RERANKING_ENABLED=false",
           "--env", "BEDROCK_KB_ID=",
           "--env", "BEDROCK_KB_FORCE_OVERRIDE=false",
           "--env", "AWS_REGION=us-east-1",
           "--env-file", "/full/path/to/file/above/.env",
           "awslabs/bedrock-kb-retrieval-mcp-server:latest"
         ],
         "env": {},
         "disabled": false,
         "autoApprove": []
       }
     }
   }
   ```

**Note**: Your credentials will need to be kept refreshed from your host.

## Usage

Once configured, the MCP server provides:

1. **Resource**: `resource://knowledgebases` - Discover available knowledge bases and their data sources
2. **Tool**: `QueryKnowledgeBases` - Query knowledge bases using natural language

### Basic Workflow

1. **Discovery**: Access the `knowledgebases` resource to see available knowledge bases
2. **Query**: Use the `QueryKnowledgeBases` tool with:
   - `query`: Your natural language question
   - `knowledge_base_id`: Target knowledge base ID
   - Optional parameters for filtering and reranking

### Example Queries

```json
{
  "query": "What are the best practices for AWS Lambda?",
  "knowledge_base_id": "EXAMPLEKBID",
  "reranking": true,
  "num_results": 5
}
```

## Limitations

- 🖼️ **Image Content**: Results with `IMAGE` content type are not included in responses
- 🌐 **Reranking Regions**: Reranking functionality is limited to [specific AWS regions](https://docs.aws.amazon.com/bedrock/latest/userguide/rerank-supported.html)
- 🔐 **Permissions**: Reranking requires additional IAM permissions and model access
