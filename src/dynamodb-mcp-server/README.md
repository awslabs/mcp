# AWS DynamoDB MCP Server

The official developer experience MCP Server for Amazon DynamoDB. This server provides DynamoDB expert design guidance and data modeling assistance.

## Available Tools

The DynamoDB MCP server provides seven tools for data modeling, validation, and code generation:

- `dynamodb_data_modeling` - Retrieves the complete DynamoDB Data Modeling Expert prompt with enterprise-level design patterns, cost optimization strategies, and multi-table design philosophy. Guides through requirements gathering, access pattern analysis, and schema design.

  **Example invocation:** "Design a data model for my e-commerce application using the DynamoDB data modeling MCP server"

- `dynamodb_data_model_validation` - Validates your DynamoDB data model by loading dynamodb_data_model.json, setting up DynamoDB Local, creating tables with test data, and executing all defined access patterns. Saves detailed validation results to dynamodb_model_validation.json.

  **Example invocation:** "Validate my DynamoDB data model"

- `source_db_analyzer` - Analyzes existing MySQL databases to extract schema structure, access patterns from Performance Schema, and generates timestamped analysis files for use with dynamodb_data_modeling. Supports both RDS Data API-based access and connection-based access.

  **Example invocation:** "Analyze my MySQL database and help me design a DynamoDB data model"

- `generate_resources` - Generates various resources from the DynamoDB data model JSON file (dynamodb_data_model.json). Currently only the `cdk` resource type is supported. Passing `cdk` as `resource_type` parameter generates a CDK app to deploy DynamoDB tables. The CDK app reads the dynamodb_data_model.json to create tables with proper configuration.

  **Example invocation:** "Generate the resources to deploy my DynamoDB data model using CDK"

- `dynamodb_data_model_schema_converter` - Converts your data model (dynamodb_data_model.md) into a structured schema.json file representing your DynamoDB tables, indexes, entities, fields, and access patterns. This machine-readable format is used for code generation and can be extended for other purposes like documentation generation or infrastructure provisioning. Automatically validates the schema with up to 8 iterations to ensure correctness.

  **Example invocation:** "Convert my data model to schema.json for code generation"

- `dynamodb_data_model_schema_validator` - Validates schema.json files for code generation compatibility. Checks field types, operations, GSI mappings, pattern IDs, and provides detailed error messages with fix suggestions. Ensures your schema is ready for the generate_data_access_layer tool.

  **Example invocation:** "Validate my schema.json file at /path/to/schema.json"

- `generate_data_access_layer` - Generates type-safe Python code from schema.json including entity classes with field validation, repository classes with CRUD operations, fully implemented access patterns, and optional usage examples. The generated code uses Pydantic for validation and boto3 for DynamoDB operations.

  **Example invocation:** "Generate Python code from my schema.json"

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

## Schema Conversion and Code Generation

After designing your DynamoDB data model, you can convert it to a structured schema and generate reference python code. **When using the MCP tools through an LLM, this entire workflow happens automatically** - the LLM guides you through schema conversion, validation, and code generation in a single conversation without requiring manual tool invocation.

For standalone usage, you can also invoke these tools directly via CLI or manually edit schema.json files and regenerate code as needed.

> **Note:** Data model validation (`dynamodb_data_model_validation`) is optional for code generation. However, if you plan to test the generated code with `usage_examples.py` against DynamoDB Local, running validation first is recommended as it automatically sets up the tables and test data in DynamoDB Local.

### Converting Data Model to Schema

The `dynamodb_data_model_schema_converter` tool converts your human-readable data model (dynamodb_data_model.md) into a structured JSON schema representing your DynamoDB tables, indexes, entities, and access patterns. This machine-readable format enables code generation and can be extended for documentation or infrastructure provisioning.

The tool automatically validates the generated schema, providing detailed error messages and fix suggestions if validation fails. Output is saved to a timestamped folder for isolation.

**Schema Structure:**

The generated schema.json is a structured representation containing:
- **Tables**: One or more DynamoDB table definitions with partition/sort keys
- **GSI Definitions**: Global Secondary Index configurations (optional)
- **Entities**: Domain models (User, Order, Product, etc.) with typed fields
- **Field Types**: string, integer, decimal, boolean, array, object, uuid
- **Access Patterns**: Query/Scan/GetItem operations with parameter definitions and key templates
- **Key Templates**: Patterns for generating partition and sort keys (e.g., `USER#{user_id}`)

This structured format serves as the input for code generation tools.

### Validating Schema Files

The `dynamodb_data_model_schema_validator` tool validates your schema.json file to ensure it's properly formatted for code generation.

**Validation Checks:**

- Required sections (table_config, entities) exist
- All required fields are present
- Field types are valid (string, integer, decimal, boolean, array, object, uuid)
- Enum values are correct (operation types, return types)
- Pattern IDs are unique across all entities
- GSI names match between gsi_list and gsi_mappings
- Fields referenced in templates exist in entity fields
- Range conditions are valid with correct parameter counts
- Access patterns have valid operations and return types

**Security:**

Schema files must be within the current working directory or subdirectories. Path traversal attempts are blocked for security.

**Validation Output Examples:**

Success:
```
✅ Schema validation passed!
```

Error with suggestions:
```
❌ Schema validation failed:
  • entities.User.fields[0].type: Invalid type value 'strng'
    💡 Did you mean 'string'? Valid options: string, integer, decimal, boolean, array, object, uuid
```

### Generating Data Access Layer

The `generate_data_access_layer` tool generates type-safe Python code from your validated schema.json file.

**Generated Code:**

- **Entity Classes**: Pydantic models with field validation and type safety
- **Repository Classes**: CRUD operations (create, read, update, delete) for each entity
- **Access Patterns**: Fully implemented query and scan operations from your schema
- **Base Repository**: Shared functionality for all repositories
- **Usage Examples**: Sample code demonstrating how to use the generated classes (optional)
- **Configuration**: ruff.toml for code quality and formatting

**Prerequisites for Code Generation:**

The generated Python code requires these runtime dependencies:
- `pydantic>=2.0` - For entity validation and type safety
- `boto3>=1.38` - For DynamoDB operations

Install them in your project:
```bash
uv add pydantic boto3
# or
pip install pydantic boto3
```

**Optional Development Dependencies:**

For linting and formatting the generated code:
- `ruff>=0.9.7` - Python linter and formatter (recommended)

**Generated File Structure:**

```
generated_dal/
├── entities.py              # Pydantic entity models
├── repositories.py          # Repository classes with CRUD operations
├── base_repository.py       # Base repository functionality
├── transaction_service.py   # Cross-table transaction methods (if schema includes cross_table_access_patterns)
├── access_pattern_mapping.json  # Pattern ID to method mapping
├── usage_examples.py        # Sample usage code (if enabled)
└── ruff.toml               # Linting configuration
```

**Using Generated Code:**

The generated code provides type-safe entity classes and repository methods for all your access patterns:

```python
from generated_dal.repositories import UserRepository
from generated_dal.entities import User

# Initialize repository
repo = UserRepository(table_name="MyTable")

# Create a new user
user = User(user_id="123", username="username", name="John Doe")
repo.create(user)

# Query by access pattern
users = repo.get_user_by_username(username="username")

# Update user
user.name = "Jane Doe"
repo.update(user)
```

For linting and formatting the generated code with ruff:
```bash
ruff check generated_dal/        # Check for issues
ruff check --fix generated_dal/  # Auto-fix issues
ruff format generated_dal/       # Format code
```
