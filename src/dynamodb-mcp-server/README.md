# AWS DynamoDB MCP Server

The official developer experience MCP Server for Amazon DynamoDB. This server provides DynamoDB expert design guidance and data modeling assistance.

## Available Tools

The DynamoDB MCP server provides four tools for data modeling and validation:

- `dynamodb_data_modeling` - Retrieves the complete DynamoDB Data Modeling Expert prompt with enterprise-level design patterns, cost optimization strategies, and multi-table design philosophy. Guides through requirements gathering, access pattern analysis, and schema design.

  **Example invocation:** "Design a data model for my e-commerce application using the DynamoDB data modeling MCP server"

- `dynamodb_data_model_validation` - Validates your DynamoDB data model by loading dynamodb_data_model.json, setting up DynamoDB Local, creating tables with test data, and executing all defined access patterns. Saves detailed validation results to dynamodb_model_validation.json.

  **Example invocation:** "Validate my DynamoDB data model"

- `source_db_analyzer` - Analyzes existing MySQL/Aurora databases to extract schema structure, access patterns from Performance Schema, and generates timestamped analysis files for use with dynamodb_data_modeling. Requires AWS RDS Data API and credentials in Secrets Manager.

  **Example invocation:** "Analyze my MySQL database and help me design a DynamoDB data model"

- `execute_dynamodb_command` - Executes AWS CLI DynamoDB commands against DynamoDB Local or AWS DynamoDB. Supports all DynamoDB API operations and automatically configures credentials for local testing.

  **Example invocation:** "Create the tables from the data model that was just created in my account in region us-east-1"

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Set up AWS credentials with access to AWS services

## Installation

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.dynamodb-mcp-server&config=JTdCJTIyY29tbWFuZCUyMiUzQSUyMnV2eCUyMGF3c2xhYnMuZHluYW1vZGItbWNwLXNlcnZlciU0MGxhdGVzdCUyMiUyQyUyMmVudiUyMiUzQSU3QiUyMkFXU19QUk9GSUxFJTIyJTNBJTIyZGVmYXVsdCUyMiUyQyUyMkFXU19SRUdJT04lMjIlM0ElMjJ1cy13ZXN0LTIlMjIlMkMlMjJGQVNUTUNQX0xPR19MRVZFTCUyMiUzQSUyMkVSUk9SJTIyJTdEJTJDJTIyZGlzYWJsZWQlMjIlM0FmYWxzZSUyQyUyMmF1dG9BcHByb3ZlJTIyJTNBJTVCJTVEJTdE)| [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=DynamoDB%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.dynamodb-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-west-2%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

Add the MCP to your favorite agentic tools (e.g. for Amazon Q Developer CLI MCP `~/.aws/amazonq/mcp.json`, or [Kiro CLI](https://kiro.dev/docs/cli/migrating-from-q/) which is replacing Amazon Q Developer CLI):

```json
{
  "mcpServers": {
    "awslabs.dynamodb-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.dynamodb-mcp-server@latest"],
      "env": {
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
      }
    }
  }
}
```

### Docker Installation

After a successful `docker build -t awslabs/dynamodb-mcp-server .`:

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

## Data Modeling

### Data Modeling in Natural Language

Use the `dynamodb_data_modeling` tool to design DynamoDB data models through natural language conversation with your AI agent. Simply ask: "use my DynamoDB MCP to help me design a DynamoDB data model."

The tool provides a structured workflow that translates application requirements into DynamoDB data models:

**Requirements Gathering Phase:**
- Captures access patterns through natural language conversation
- Documents entities, relationships, and read/write patterns
- Records estimated requests per second (RPS) for each pattern
- Creates `dynamodb_requirements.md` file that updates in real-time
- Identifies patterns better suited for other AWS services (OpenSearch for text search, Redshift for analytics)
- Flags special design considerations (e.g., massive fan-out patterns requiring DynamoDB Streams and Lambda)

**Design Phase:**
- Generates optimized table and index designs
- Creates `dynamodb_data_model.md` with detailed design rationale
- Provides estimated monthly costs
- Documents how each access pattern is supported
- Includes optimization recommendations for scale and performance

The tool is backed by expert-engineered context that helps reasoning models guide you through advanced modeling techniques. Best results are achieved with reasoning-capable models such as Amazon Q, Anthropic Claude 4/4.5 Sonnet, OpenAI o3, and Google Gemini 2.5.

### Data Model Validation

**Prerequisites for Data Model Validation:**
To use the data model validation tool, you need one of the following:
- **Container Runtime**: Docker, Podman, Finch, or nerdctl with a running daemon
- **Java Runtime**: Java JRE version 17 or newer (set `JAVA_HOME` or ensure `java` is in your system PATH)

After completing your data model design, use the `dynamodb_data_model_validation` tool to automatically test your data model against DynamoDB Local. The validation tool closes the loop between generation and execution by creating an iterative validation cycle.

**How It Works:**

The tool automates the traditional manual validation process:

1. **Setup**: Spins up DynamoDB Local environment (Docker/Podman/Finch/nerdctl or Java fallback)
2. **Generate Test Specification**: Creates `dynamodb_data_model.json` listing tables, sample data, and access patterns to test
3. **Deploy Schema**: Creates tables, indexes, and inserts sample data locally
4. **Execute Tests**: Runs all read and write operations defined in your access patterns
5. **Validate Results**: Checks that each access pattern behaves correctly and efficiently
6. **Iterative Refinement**: If validation fails (e.g., query returns incomplete results due to misaligned partition key), the tool records the issue, and regenerates the affected schema and rerun tests until all patterns pass

**Validation Output:**

- `dynamodb_model_validation.json`: Detailed validation results with pattern responses
- `validation_result.md`: Summary of validation process with pass/fail status for each access pattern
- Identifies issues like incorrect key structures, missing indexes, or inefficient query patterns

### Source Database Analysis

The `source_db_analyzer` tool analyzes existing MySQL/Aurora databases to extract schema and access patterns for DynamoDB modeling. This is useful when migrating from relational databases.

#### Prerequisites for MySQL Integration

1. Aurora MySQL Cluster with credentials stored in AWS Secrets Manager
2. Enable RDS Data API for your Aurora MySQL Cluster
3. Enable Performance Schema for access pattern analysis (optional but recommended):
   - Set `performance_schema` parameter to 1 in your DB parameter group
   - Reboot the DB instance after changes
   - Verify with: `SHOW GLOBAL VARIABLES LIKE '%performance_schema'`
   - Consider tuning:
     - `performance_schema_digests_size` - Maximum rows in events_statements_summary_by_digest
     - `performance_schema_max_digest_length` - Maximum byte length per statement digest (default: 1024)
   - Without Performance Schema, analysis is based on information schema only

4. AWS credentials with permissions to access RDS Data API and AWS Secrets Manager

#### MySQL Environment Variables

Add these environment variables to enable MySQL integration:

- `MYSQL_CLUSTER_ARN`: Aurora MySQL cluster Resource ARN
- `MYSQL_SECRET_ARN`: ARN of secret containing database credentials
- `MYSQL_DATABASE`: Database name to analyze
- `AWS_REGION`: AWS region of the Aurora MySQL cluster
- `MYSQL_MAX_QUERY_RESULTS`: Maximum rows in analysis output files (optional, default: 500)

#### MCP Configuration with MySQL

```json
{
  "mcpServers": {
    "awslabs.dynamodb-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.dynamodb-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "ERROR",
        "MYSQL_CLUSTER_ARN": "arn:aws:rds:$REGION:$ACCOUNT_ID:cluster:$CLUSTER_NAME",
        "MYSQL_SECRET_ARN": "arn:aws:secretsmanager:$REGION:$ACCOUNT_ID:secret:$SECRET_NAME",
        "MYSQL_DATABASE": "<DATABASE_NAME>",
        "MYSQL_MAX_QUERY_RESULTS": 500
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

#### Using Source Database Analysis

1. Run `source_db_analyzer` against your MySQL database
2. Review the generated timestamped analysis folder (database_analysis_YYYYMMDD_HHMMSS)
3. Read the manifest.md file first - it lists all analysis files and statistics
4. Read all analysis files to understand schema structure and access patterns
5. Use the analysis with `dynamodb_data_modeling` to design your DynamoDB schema

The tool generates Markdown files with:
- Schema structure (tables, columns, indexes, foreign keys)
- Access patterns from Performance Schema (query patterns, RPS, frequencies)
- Timestamped analysis for tracking changes over time
