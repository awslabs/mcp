# AWS DynamoDB MCP Server

The official developer experience MCP Server for Amazon DynamoDB. This server provides DynamoDB expert design guidance and data modeling assistance.

## Available MCP Tools

Right now the DynamoDB MCP server contains two tools that support data modeling tasks. You can design a data model in natural language by using only the `dynamodb_data_modeling` tool or you can analyze your MySQL database and convert the analysis into a DynamoDB data model by using the `source_db_analyzer` tool.

### Design & Modeling

* `dynamodb_data_modeling` - Retrieves the complete DynamoDB Data Modeling Expert prompt
* `source_db_analyzer` - Executes predefined SQL queries against source databases to analyze schema and access patterns

## Migration Notice

Starting with version 2.0.0, this server focuses exclusively on DynamoDB design and modeling guidance. All operational DynamoDB management tools (table operations, item operations, queries, backups, etc.) have been removed in favor of the [AWS API MCP Server](https://github.com/awslabs/mcp/tree/main/src/aws-api-mcp-server) which provides the same capability and more.

**This server does not do:**

- ❌ Operational DynamoDB management (CRUD operations)
- ❌ Table creation or data migration
- ❌ Direct data queries or transformations

### Recommended: AWS API MCP Server

For operational DynamoDB management (retrieving data, managing tables, etc.), use the [AWS API MCP Server](https://github.com/awslabs/mcp/tree/main/src/aws-api-mcp-server) which provides comprehensive DynamoDB operations. [Migration guide available here](https://github.com/awslabs/mcp/tree/main/src/aws-api-mcp-server).

### Not Recommended: Legacy Version

If you must use the previous operational tools, you can pin to version 1.0.9, though this is not recommended:

```json
{
  "mcpServers": {
    "awslabs.dynamodb-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.dynamodb-mcp-server@1.0.9"],
      "env": {
        "DDB-MCP-READONLY": "true",
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Instructions

To design a data model in natural language you can simply ask your AI agent to “use my DynamoDB MCP to help me design a DynamoDB data model,” or something similar. If you want to analyze your MySQL query patterns then you can follow these additional steps below to setup connectivity and then say something like “analyze my MySQL database and then help me design a DynamoDB data model.”

## Source Database Integration

The DynamoDB MCP server includes source database integration for database analysis and the tool `source_db_analyzer` is useful to get the actual source database schema and access patterns which helps to design the model in DynamoDB. We recommend running this tool against a non-production database instance and it currently supports Aurora MySQL with additional database support planned for future releases.

### Prerequisites for MySQL Integration

1. Aurora MySQL Cluster with MySQL username and password stored in AWS Secrets Manager
2. Enable RDS Data API for your Aurora MySQL Cluster
3. Enable Performance Schema for access pattern analysis (optional):

    * Go to the parameter group for your DB instance and set performance_schema value to 1. Make sure to reboot the DB instance after the changes whenever you turn the Performance Schema on or off. Follow the [Instructions](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/USER_WorkingWithParamGroups.Modifying.html) to modify DB parameter group in Amazon Aurora.
    * After the parameter values are modified, you can run the "SHOW GLOBAL VARIABLES LIKE'%performance_schema'"; command to view the value of the performance_schema parameter of the database instance, also consider tunning the below parameters if required.
    * `performance_schema_digests_size` [parameter](https://dev.mysql.com/doc/refman/8.0/en/performance-schema-system-variables.html#sysvar_performance_schema_digests_size) - Sets the maximum number of rows stored in the events_statements_summary_by_digest table for querying access pattern. (When you hit this limit, some logs will be lost, potentially missing important access patterns)
    * `performance_schema_max_digest_length` [parameter](https://dev.mysql.com/doc/refman/8.0/en/performance-schema-system-variables.html#sysvar_performance_schema_max_digest_length) - Sets the maximum byte length for each individual statement digest (access pattern) that the Performance Schema stores. (Default is 1024 bytes, Complex queries might not be fully captured when you hit this limit)
    * Without these Performance Schema query access patterns, DynamoDB Data Modeler tool recommends access patterns based on the information schema from the source Database.

1. Set up AWS credentials with access to AWS services:

    * Configure AWS credentials with `aws configure` or environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN) . The server will automatically use credentials from environment variables or other standard AWS credential sources.
    * AWS profile with permissions to access RDS Data API and AWS Secrets Manager

### MySQL Environment Variables

Add these environment variables to DynamoDB MCP Server configuration to enable MySQL integration:

* `MYSQL_CLUSTER_ARN`: The Resource ARN of the Aurora MySQL cluster
* `MYSQL_SECRET_ARN`: The ARN of the secret containing database credentials
* `MYSQL_DATABASE`: The name of the database to connect to
* `AWS_REGION`: AWS region of the Aurora MySQL cluster
* `MYSQL_MAX_QUERY_RESULTS`: Maximum number of rows to include in analysis output files for schema and access_pattern logs (optional, default: "500")

### MCP configuration with MySQL Environment Variables

```json
{
  "mcpServers": {
    "awslabs.dynamodb-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.dynamodb-mcp-server@latest"],
      "env": {
        "DDB-MCP-READONLY": "true",
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "ERROR",
        "MYSQL_CLUSTER_ARN":"arn:aws:rds:$REGION:$ACCOUNT_ID:cluster:$CLUSTER_NAME",
        "MYSQL_SECRET_ARN":"arn:aws:secretsmanager:$REGION:$ACCOUNT_ID:secret:$SECRET_NAME",
        "MYSQL_DATABASE":"<DATABASE_NAME>",
        "MYSQL_MAX_QUERY_RESULTS": 500
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Set up AWS credentials with access to AWS services

    * Consider setting up Read-only permission if you don't want the LLM to modify any resources

## Installation

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.dynamodb-mcp-server&config=JTdCJTIyY29tbWFuZCUyMiUzQSUyMnV2eCUyMGF3c2xhYnMuZHluYW1vZGItbWNwLXNlcnZlciU0MGxhdGVzdCUyMiUyQyUyMmVudiUyMiUzQSU3QiUyMkREQi1NQ1AtUkVBRE9OTFklMjIlM0ElMjJ0cnVlJTIyJTJDJTIyQVdTX1BST0ZJTEUlMjIlM0ElMjJkZWZhdWx0JTIyJTJDJTIyQVdTX1JFR0lPTiUyMiUzQSUyMnVzLXdlc3QtMiUyMiUyQyUyMkZBU1RNQ1BfTE9HX0xFVkVMJTIyJTNBJTIyRVJST1IlMjIlN0QlMkMlMjJkaXNhYmxlZCUyMiUzQWZhbHNlJTJDJTIyYXV0b0FwcHJvdmUlMjIlM0ElNUIlNUQlN0Q%3D)| [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=DynamoDB%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.dynamodb-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22DDB-MCP-READONLY%22%3A%22true%22%2C%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-west-2%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

Add the MCP to your favorite agentic tools. (e.g. for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.dynamodb-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.dynamodb-mcp-server@latest"],
      "env": {
        "DDB-MCP-READONLY": "true",
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.dynamodb-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.dynamodb-mcp-server@latest",
        "awslabs.dynamodb-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-west-2"
      }
    }
  }
}
```


or docker after a successful `docker build -t awslabs/dynamodb-mcp-server .`:

```json
  {
    "mcpServers": {
      "awslabs.dynamodb-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "--env",
          "FASTMCP_LOG_LEVEL=ERROR",
          "awslabs/dynamodb-mcp-server:latest"
        ],
        "env": {},
        "disabled": false,
        "autoApprove": []
      }
    }
  }
```

## Limitations & Considerations

### **Application-Level Patterns:**

* Queries generated dynamically in application code
* Caching layer behavior (Redis, Memcached)
* Real-time vs. analytics query differentiation
* Background job access patterns

### Business Context:

* Data consistency requirements
* Compliance and audit requirements
* Geographic distribution requirements

### Recommendation:

Supplement analysis with documentation or natural language descriptions based on:

* Application code review
* Architecture documentation review
* Stakeholder interviews with development team
* Load testing results analysis

There are also more complex patterns that result from stored procedures, triggers, aggregations, that the tool does not currently handle consistently but we plan to improve in future iterations.
