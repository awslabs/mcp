# AWS DynamoDB MCP Server

The official developer experience MCP Server for Amazon DynamoDB. This server provides DynamoDB expert design guidance and data modeling assistance.

## Available Tools

The DynamoDB MCP server provides four tools for data modeling and validation:

- `dynamodb_data_modeling` - Retrieves the complete DynamoDB Data Modeling Expert prompt with enterprise-level design patterns, cost optimization strategies, and multi-table design philosophy. Guides through requirements gathering, access pattern analysis, and schema design.

  **Example invocation:** "Design a data model for my e-commerce application using the DynamoDB data modeling MCP server"

- `dynamodb_data_model_validation` - Validates your DynamoDB data model by loading dynamodb_data_model.json, setting up DynamoDB Local, creating tables with test data, and executing all defined access patterns. Saves detailed validation results to dynamodb_model_validation.json.

  **Example invocation:** "Validate my DynamoDB data model"

- `source_db_analyzer` - Analyzes existing MySQL databases to extract schema structure, access patterns from Performance Schema, and generates timestamped analysis files for use with dynamodb_data_modeling. Supports both RDS Data API-based access and connection-based access.

  **Example invocation:** "Analyze my MySQL database and help me design a DynamoDB data model"

- `execute_dynamodb_command` - Executes AWS CLI DynamoDB commands against DynamoDB Local or AWS DynamoDB. Supports all DynamoDB API operations and automatically configures credentials for local testing.

  **Example invocation:** "Create the tables from the data model that was just created in my account in region us-east-1"

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Set up AWS credentials with access to AWS services

## Installation

| Kiro   | Cursor  | VS Code |
|:------:|:-------:|:-------:|
| [![Kiro](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.dynamodb-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.dynamodb-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22DDB-MCP-READONLY%22%3A%22true%22%2C%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-west-2%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D)| [![Cursor](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.dynamodb-mcp-server&config=JTdCJTIyY29tbWFuZCUyMiUzQSUyMnV2eCUyMGF3c2xhYnMuZHluYW1vZGItbWNwLXNlcnZlciU0MGxhdGVzdCUyMiUyQyUyMmVudiUyMiUzQSU3QiUyMkFXU19QUk9GSUxFJTIyJTNBJTIyZGVmYXVsdCUyMiUyQyUyMkFXU19SRUdJT04lMjIlM0ElMjJ1cy13ZXN0LTIlMjIlMkMlMjJGQVNUTUNQX0xPR19MRVZFTCUyMiUzQSUyMkVSUk9SJTIyJTdEJTJDJTIyZGlzYWJsZWQlMjIlM0FmYWxzZSUyQyUyMmF1dG9BcHByb3ZlJTIyJTNBJTVCJTVEJTdE)| [![VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=DynamoDB%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.dynamodb-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-west-2%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

> **Note:** The install buttons above configure `AWS_REGION` to `us-west-2` by default. Update this value in your MCP configuration after installation if you need a different region.

Add the MCP server to your configuration file (for [Kiro](https://kiro.dev/docs/mcp/) add to `.kiro/settings/mcp.json` - see [configuration path](https://kiro.dev/docs/cli/mcp/configuration/#mcp-server-loading-priority)):

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
        "FASTMCP_LOG_LEVEL": "ERROR"
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

The tool is backed by expert-engineered context that helps reasoning models guide you through advanced modeling techniques. Best results are achieved with reasoning-capable models such as Anthropic Claude 4/4.5 Sonnet, OpenAI o3, and Google Gemini 2.5.

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

The `source_db_analyzer` tool extracts schema and access patterns from your existing database to help design your DynamoDB model. This is useful when migrating from relational databases.

The tool supports two connection methods for MySQL:
- **RDS Data API-based access**: Serverless connection using cluster ARN
- **Connection-based access**: Traditional connection using hostname/port

**Supported Databases:**
- MySQL / Aurora MySQL
- PostgreSQL
- SQL Server

**Execution Modes:**
- **Self-Service Mode**: Generate SQL queries, run them yourself, provide results (MYSQL, PSQL, MSSQL)
- **Managed Mode**: Direct connection via AWS RDS Data API (MySQL only)

We recommend running this tool against a non-production database instance.

### Self-Service Mode (MYSQL, PSQL, MSSQL)

Self-service mode allows you to analyze any database without AWS connectivity:

1. **Generate Queries**: Tool writes SQL queries (based on selected database) to a file
2. **Run Queries**: You execute queries against your database
3. **Provide Results**: Tool parses results and generates analysis

### Managed Mode (MYSQL, PSQL, MSSQL)

Managed mode allow you to connect tool, to AWS RDS Data API, to analyzes existing MySQL/Aurora databases to extract schema and access patterns for DynamoDB modeling.

#### Prerequisites for MySQL Integration (Managed Mode)

**For RDS Data API-based access:**
1. MySQL cluster with RDS Data API enabled
2. Database credentials stored in AWS Secrets Manager
3. AWS credentials with permissions to access RDS Data API and Secrets Manager

**For Connection-based access:**
1. MySQL server accessible from your environment
2. Database credentials stored in AWS Secrets Manager
3. AWS credentials with permissions to access Secrets Manager

**For both connection methods:**
4. Enable Performance Schema for access pattern analysis (optional but recommended):
   - Set `performance_schema` parameter to 1 in your DB parameter group
   - Reboot the DB instance after changes
   - Verify with: `SHOW GLOBAL VARIABLES LIKE '%performance_schema'`
   - Consider tuning:
     - `performance_schema_digests_size` - Maximum rows in events_statements_summary_by_digest
     - `performance_schema_max_digest_length` - Maximum byte length per statement digest (default: 1024)
   - Without Performance Schema, analysis is based on information schema only

#### MySQL Environment Variables

Add these environment variables to enable MySQL integration:

**For RDS Data API-based access:**
- `MYSQL_CLUSTER_ARN`: MySQL cluster ARN
- `MYSQL_SECRET_ARN`: ARN of secret containing database credentials
- `MYSQL_DATABASE`: Database name to analyze
- `AWS_REGION`: AWS region of the cluster

**For Connection-based access:**
- `MYSQL_HOSTNAME`: MySQL server hostname or endpoint
- `MYSQL_PORT`: MySQL server port (optional, default: 3306)
- `MYSQL_SECRET_ARN`: ARN of secret containing database credentials
- `MYSQL_DATABASE`: Database name to analyze
- `AWS_REGION`: AWS region where Secrets Manager is located

**Common options:**
- `MYSQL_MAX_QUERY_RESULTS`: Maximum rows in analysis output files (optional, default: 500)

**Note:** Explicit tool parameters take precedence over environment variables. Only one connection method (cluster ARN or hostname) should be specified.

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

1. Run `source_db_analyzer` against your Database (Self-service or Managed mode)
2. Review the generated timestamped analysis folder (database_analysis_YYYYMMDD_HHMMSS)
3. Read the manifest.md file first - it lists all analysis files and statistics
4. Read all analysis files to understand schema structure and access patterns
5. Use the analysis with `dynamodb_data_modeling` to design your DynamoDB schema

The tool generates Markdown files with:
- Schema structure (tables, columns, indexes, foreign keys)
- Access patterns from Performance Schema (query patterns, RPS, frequencies)
- Timestamped analysis for tracking changes over time
