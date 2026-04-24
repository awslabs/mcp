# Migration Guide: Core MCP Server

This guide helps you migrate from `awslabs.core-mcp-server` to configuring individual MCP servers directly in your client.

## Why We're Deprecating

The `core-mcp-server` was designed as a proxy that bundles 45+ MCP servers behind role-based environment variables. While useful early on, it has several issues:

- **Modern MCP clients handle multi-server configs natively** — Kiro, Cursor, and VS Code all support configuring multiple MCP servers directly, making the proxy pattern unnecessary
- **Massive dependency footprint** — Installing core-mcp-server pulls in every bundled server, causing slow installs and build failures (e.g., cassandra-driver compilation issues)
- **Tool name overflow** — Proxied tool names with prefixes can exceed the 64-character API limit in some clients
- **Bundles deprecated servers** — Several servers included in the core bundle have been deprecated

## How to Migrate

Instead of using core-mcp-server with role environment variables, configure the individual servers you need directly in your MCP client config.

### Example: Before (core-mcp-server)

```json
{
  "mcpServers": {
    "awslabs-core-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.core-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "aws-foundation": "true",
        "serverless-architecture": "true"
      }
    }
  }
}
```

### Example: After (individual servers)

```json
{
  "mcpServers": {
    "awslabs.aws-api-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-api-mcp-server@latest"],
      "env": { "AWS_REGION": "us-east-1", "FASTMCP_LOG_LEVEL": "ERROR" }
    },
    "awslabs.aws-serverless-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-serverless-mcp-server@latest"],
      "env": { "AWS_PROFILE": "your-profile", "AWS_REGION": "us-east-1", "FASTMCP_LOG_LEVEL": "ERROR" }
    },
    "awslabs.lambda-tool-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.lambda-tool-mcp-server@latest"],
      "env": { "AWS_PROFILE": "your-profile", "AWS_REGION": "us-east-1", "FASTMCP_LOG_LEVEL": "ERROR" }
    }
  }
}
```

## Role-to-Server Mapping

Use this table to find the individual servers for each role you were using:

| Role | Individual Servers |
|---|---|
| `aws-foundation` | [aws-api-mcp-server](../src/aws-api-mcp-server), [aws-knowledge-mcp-server](../src/aws-knowledge-mcp-server) |
| `dev-tools` | [code-doc-gen-mcp-server](../src/code-doc-gen-mcp-server), [aws-knowledge-mcp-server](../src/aws-knowledge-mcp-server) |
| `ci-cd-devops` | [cdk-mcp-server](../src/cdk-mcp-server), [aws-iac-mcp-server](../src/aws-iac-mcp-server) |
| `container-orchestration` | [eks-mcp-server](../src/eks-mcp-server), [ecs-mcp-server](../src/ecs-mcp-server), [finch-mcp-server](../src/finch-mcp-server) |
| `serverless-architecture` | [aws-serverless-mcp-server](../src/aws-serverless-mcp-server), [lambda-tool-mcp-server](../src/lambda-tool-mcp-server), [stepfunctions-tool-mcp-server](../src/stepfunctions-tool-mcp-server), [amazon-sns-sqs-mcp-server](../src/amazon-sns-sqs-mcp-server) |
| `analytics-warehouse` | [redshift-mcp-server](../src/redshift-mcp-server), [timestream-for-influxdb-mcp-server](../src/timestream-for-influxdb-mcp-server), [aws-dataprocessing-mcp-server](../src/aws-dataprocessing-mcp-server) |
| `data-platform-eng` | [dynamodb-mcp-server](../src/dynamodb-mcp-server), [s3-tables-mcp-server](../src/s3-tables-mcp-server), [aws-dataprocessing-mcp-server](../src/aws-dataprocessing-mcp-server) |
| `frontend-dev` | No active replacement — previously bundled deprecated servers |
| `solutions-architect` | [aws-pricing-mcp-server](../src/aws-pricing-mcp-server), [cost-analysis-mcp-server](../src/cost-analysis-mcp-server), [aws-knowledge-mcp-server](../src/aws-knowledge-mcp-server) |
| `finops` | [billing-cost-management-mcp-server](../src/billing-cost-management-mcp-server), [aws-pricing-mcp-server](../src/aws-pricing-mcp-server), [cloudwatch-mcp-server](../src/cloudwatch-mcp-server) |
| `monitoring-observability` | [cloudwatch-mcp-server](../src/cloudwatch-mcp-server), [cloudwatch-applicationsignals-mcp-server](../src/cloudwatch-applicationsignals-mcp-server), [prometheus-mcp-server](../src/prometheus-mcp-server), [cloudtrail-mcp-server](../src/cloudtrail-mcp-server) |
| `caching-performance` | [elasticache-mcp-server](../src/elasticache-mcp-server), [memcached-mcp-server](../src/memcached-mcp-server) |
| `security-identity` | [iam-mcp-server](../src/iam-mcp-server), [aws-support-mcp-server](../src/aws-support-mcp-server), [well-architected-security-mcp-server](../src/well-architected-security-mcp-server) |
| `sql-db-specialist` | [postgres-mcp-server](../src/postgres-mcp-server), [mysql-mcp-server](../src/mysql-mcp-server), [aurora-dsql-mcp-server](../src/aurora-dsql-mcp-server), [redshift-mcp-server](../src/redshift-mcp-server) |
| `nosql-db-specialist` | [dynamodb-mcp-server](../src/dynamodb-mcp-server), [documentdb-mcp-server](../src/documentdb-mcp-server), [amazon-keyspaces-mcp-server](../src/amazon-keyspaces-mcp-server), [amazon-neptune-mcp-server](../src/amazon-neptune-mcp-server) |
| `timeseries-db-specialist` | [timestream-for-influxdb-mcp-server](../src/timestream-for-influxdb-mcp-server), [prometheus-mcp-server](../src/prometheus-mcp-server), [cloudwatch-mcp-server](../src/cloudwatch-mcp-server) |
| `messaging-events` | [amazon-sns-sqs-mcp-server](../src/amazon-sns-sqs-mcp-server), [amazon-mq-mcp-server](../src/amazon-mq-mcp-server) |
| `healthcare-lifesci` | [aws-healthomics-mcp-server](../src/aws-healthomics-mcp-server) |

> **Note:** The `dev-tools` role previously included `git-repo-research-mcp-server` (deprecated — use [Context7](https://github.com/upstash/context7) instead). The `solutions-architect` role previously included `diagram-mcp-server` and `cost-explorer-mcp-server` (both deprecated). The `ci-cd-devops` role previously included `cfn-mcp-server` (deprecated — use `aws-iac-mcp-server`).

## The `prompt_understanding` Tool

The core server's only unique tool, `prompt_understanding`, returns a static Markdown document with AWS architecture guidance. This content can be included directly in your project's CLAUDE.md, `.cursorrules`, or equivalent AI assistant configuration file instead.

## Summary

Remove `core-mcp-server` from your config and add the individual servers you actually need. This gives you faster installs, no tool name conflicts, and direct control over which servers are active. See the [full server list](https://github.com/awslabs/mcp#available-mcp-servers-quick-installation) for all available options.
