# Core MCP Server

MCP server that provides a starting point for using AWS MCP servers through a dynamic proxy server strategy based on role-based environment variables.

## Features

### Planning and orchestration

- Provides tool for prompt understanding and translation to AWS services

### Dynamic Proxy Server Strategy

The Core MCP Server implements a proxy server strategy that dynamically imports and proxies other MCP servers based on role-based environment variables. This allows you to create tailored server configurations for specific use cases or roles without having to manually configure each server.

#### Role-Based Server Configuration

You can enable specific roles by setting environment variables. Each role corresponds to a logical grouping of MCP servers that are commonly used together for specific use cases.

> **Important**: Environment variable names can be either lowercase with hyphens or uppercase with underscores (e.g., `aws-foundation` or `AWS_FOUNDATION`). Some systems may not support the hyphenated format, so choose the format that works best for your environment.

| Role Environment Variable | Description | Included MCP Servers |
|---------------------------|-------------|----------------------|
| `aws-foundation` | AWS knowledge and API servers | aws-knowledge-server, aws-api-server |
| `dev-tools` | Development tools | git-repo-research-server, code-doc-gen-server, aws-knowledge-server |
| `ci-cd-devops` | CI/CD and DevOps | cdk-server, cfn-server |
| `container-orchestration` | Container management | eks-server, ecs-server, finch-server |
| `serverless-architecture` | Serverless development | serverless-server, lambda-tool-server, stepfunctions-tool-server, sns-sqs-server |
| `analytics-warehouse` | Data analytics and warehousing | redshift-server, timestream-for-influxdb-server, dataprocessing-server, syntheticdata-server |
| `data-platform-eng` | Data platform engineering | dynamodb-server, s3-tables-server, dataprocessing-server |
| `frontend-dev` | Frontend development | frontend-server, nova-canvas-server |
| `solutions-architect` | Solution architecture | diagram-server, pricing-server, cost-explorer-server, syntheticdata-server, aws-knowledge-server |
| `finops` | Financial operations | cost-explorer-server, pricing-server, cloudwatch-server, billing-cost-management-server |
| `monitoring-observability` | Monitoring and observability | cloudwatch-server, cloudwatch-appsignals-server, prometheus-server, cloudtrail-server |
| `caching-performance` | Caching and performance | elasticache-server, memcached-server |
| `security-identity` | Security and identity | iam-server, support-server, well-architected-security-server |
| `sql-db-specialist` | SQL database specialist | postgres-server, mysql-server, aurora-dsql-server, redshift-server |
| `nosql-db-specialist` | NoSQL database specialist | dynamodb-server, documentdb-server, keyspaces-server, neptune-server |
| `timeseries-db-specialist` | Time series database specialist | timestream-for-influxdb-server, prometheus-server, cloudwatch-server |
| `messaging-events` | Messaging and events | sns-sqs-server, mq-server |
| `healthcare-lifesci` | Healthcare and life sciences | healthomics-server |

#### Benefits of the Proxy Server Strategy

- **Simplified Configuration**: Enable multiple servers with a single environment variable
- **Reduced Duplication**: Servers are imported only once, even if needed by multiple roles
- **Tailored Experience**: Create custom server configurations for specific use cases
- **Flexible Deployment**: Easily switch between different server configurations

#### Usage Notes

- If no roles are enabled, the Core MCP Server will still provide its basic functionality (prompt_understanding) but won't import any additional servers
- You can enable multiple roles simultaneously to create a comprehensive server configuration
- The proxy strategy ensures that each server is imported only once, even if it's needed by multiple roles

> **Note**: Not all AWS MCP servers are represented in these logical groupings. For specific use cases, you may need to install additional MCP servers directly. See the [main README](https://github.com/awslabs/mcp#available-mcp-servers-quick-installation) for a complete list of available MCP servers.

## Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer and resolver
- AWS credentials configured with Bedrock access
- Node.js (for UVX installation support)


## Installation

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.core-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuY29yZS1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImF1dG9BcHByb3ZlIjpbXSwiZGlzYWJsZWQiOmZhbHNlfQ%3D%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Core%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.core-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22autoApprove%22%3A%5B%5D%2C%22disabled%22%3Afalse%7D) |

Configure the MCP server in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.core-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.core-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "aws-foundation": "true",
        "solutions-architect": "true"
        // Add other roles as needed
      },
      "autoApprove": [],
      "disabled": false
    }
  }
}
```

To enable specific role-based server configurations, add the corresponding environment variables to the `env` section of your MCP client configuration. For example, the configuration above enables the `aws-foundation` and `solutions-architect` roles, which will import the corresponding MCP servers.
### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.core-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.core-mcp-server@latest",
        "awslabs.core-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "aws-foundation": "true",
        "solutions-architect": "true"
        // Add other roles as needed
      }
    }
  }
}
```


or docker after a successful `docker build -t awslabs/core-mcp-server .`:

```json
  {
    "mcpServers": {
      "awslabs.core-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "--env",
          "FASTMCP_LOG_LEVEL=ERROR",
          "--env",
          "aws-foundation=true",
          "--env",
          "solutions-architect=true",
          "awslabs/core-mcp-server:latest"
        ],
        "env": {},
        "disabled": false,
        "autoApprove": []
      }
    }
  }
```

## Tools and Resources

The server exposes the following tools through the MCP interface:

- `prompt_understanding` - Helps to provide guidance and planning support when building AWS Solutions for the given prompt
