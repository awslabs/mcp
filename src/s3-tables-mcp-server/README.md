# AWS S3 Tables MCP Server

Official MCP Server for interacting with AWS S3 Tables (Iceberg) with multi-engine support.

## Features

- **Control Plane Operations**: Manage table buckets, namespaces, and Iceberg tables
- **Data Plane Operations**: Query, preview, and analyze table data
- **Multi-Engine Support**: DuckDB, Amazon Athena, and EMR Serverless
- **MCP Resources**: Access table buckets, namespaces, and tables as resources
- **Schema Validation**: Robust data models with Pydantic validation
- **Error Handling**: Comprehensive error handling and logging

## Quick Start

### 1. Installation

```bash
cd src/s3-tables-mcp-server
pip install -e .
```

### 2. Basic Testing (No AWS Required)

```bash
# Test imports and basic functionality
python simple_test.py

# Test full MCP server functionality  
python test_mcp_client.py
```

### 3. Start the Server

```bash
# For MCP clients (recommended)
python -m awslabs.s3_tables_mcp_server.server --sse

# Direct execution
python awslabs/s3_tables_mcp_server/server.py
```

## Available Tools

### Control Plane
- `create_table_bucket` - Create S3 Tables bucket
- `get_table_bucket` - Get bucket information
- `delete_table_bucket` - Delete bucket
- `create_namespace` - Create namespace
- `get_namespace` - Get namespace info
- `delete_namespace` - Delete namespace
- `create_table` - Create Iceberg table
- `get_table` - Get table information
- `delete_table` - Delete table
- `rename_table` - Rename table

### Data Plane
- `query_table` - Execute SQL queries
- `preview_table` - Preview table data
- `describe_table_schema` - Get schema info
- `insert_data` - Insert data
- `optimize_table` - Optimize storage

### Utilities
- `test_engines` - Test engine connectivity

## Available Resources

- `resource://table-buckets` - List all table buckets
- `resource://namespaces` - List all namespaces
- `resource://tables` - List all tables

## Supported Query Engines

1. **DuckDB** (Default)
   - Fast local queries
   - Great for development and testing
   - No additional setup required

2. **Amazon Athena**
   - Serverless SQL queries
   - Production-ready
   - Requires AWS configuration

3. **EMR Serverless**
   - Spark-based processing
   - Large-scale data processing
   - Requires EMR application setup

## Configuration

### Environment Variables

**Create a `.env` file** from the template:
```bash
cp .env.template .env
# Edit .env with your values
```

**Key Environment Variables:**

```bash
# Required AWS Configuration
AWS_ACCOUNT_ID=123456789012          # Your 12-digit AWS account ID
AWS_REGION=us-west-2                 # AWS region to use

# Optional AWS Configuration  
AWS_PROFILE=                         # AWS profile name (leave empty for default)

# S3 Tables Configuration
S3_TABLES_BUCKET=my-test-bucket      # Default bucket name
S3_TABLES_NAMESPACE=default          # Default namespace

# Lake Formation Integration
LAKE_FORMATION_ROLE_NAME=S3TablesRoleForLakeFormation
S3_TABLES_CATALOG_NAME=s3tablescatalog

# Athena Configuration (optional)
ATHENA_WORKGROUP=primary
ATHENA_RESULTS_LOCATION=s3://aws-athena-query-results-${AWS_ACCOUNT_ID}-${AWS_REGION}/

# EMR Serverless (optional)
EMR_SERVERLESS_APPLICATION_ID=your_app_id
EMR_SERVERLESS_JOB_ROLE_ARN=your_role_arn

# Logging
LOG_LEVEL=INFO
FASTMCP_LOG_LEVEL=INFO
```

**No Hardcoded Values:** All account IDs, usernames, and AWS resources are configurable via environment variables.

## Integration with MCP Clients

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "s3-tables": {
      "command": "python",
      "args": [
        "/path/to/mcp/src/s3-tables-mcp-server/awslabs/s3_tables_mcp_server/server.py",
        "--sse"
      ],
      "env": {
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

## Example Usage

### Query a Table

```python
# Through MCP client
{
  "method": "tools/call",
  "params": {
    "name": "query_table",
    "arguments": {
      "table_arn": "arn:aws:s3tables:us-east-1:123456789012:bucket/my-bucket/table/my-table",
      "sql_query": "SELECT * FROM table WHERE status = 'active' LIMIT 10",
      "engine": "duckdb"
    }
  }
}
```

### Create a Table

```python
{
  "method": "tools/call", 
  "params": {
    "name": "create_table",
    "arguments": {
      "table_bucket_arn": "arn:aws:s3tables:us-east-1:123456789012:bucket/my-bucket",
      "namespace": "analytics",
      "name": "user_events",
      "schema_fields": [
        {"name": "user_id", "type": "string", "required": true},
        {"name": "event_type", "type": "string", "required": true},
        {"name": "timestamp", "type": "timestamp", "required": true},
        {"name": "properties", "type": "map<string,string>", "required": false}
      ]
    }
  }
}
```

## Development

### Running Tests

```bash
# Basic functionality tests
python test_basic_functionality.py

# MCP client tests
python test_mcp_client.py

# Engine-specific tests
python -c "
import asyncio
from awslabs.s3_tables_mcp_server.server import engine_manager
print(asyncio.run(engine_manager.test_engines()))
"
```

### Mock Testing

The server supports mock operations for development without AWS resources:

```python
from awslabs.s3_tables_mcp_server.models import QueryResult, QueryEngine

# Mock successful query result
mock_result = QueryResult(
    status='success',
    rows_returned=100,
    execution_time_ms=250.5,
    engine_used=QueryEngine.DUCKDB,
    data=[{'id': 1, 'name': 'test'}],
    schema={'columns': ['id', 'name']}
)
```

## Status

🟢 **Ready for Testing** - Basic operations work without AWS resources  
🟡 **AWS Integration** - Requires AWS credentials for live operations  
🟢 **MCP Protocol** - Full MCP server implementation ready  
🟢 **Multi-Engine** - DuckDB, Athena, and Spark support implemented  

## Next Steps

1. **Test Basic Functionality**: Run the provided test scripts
2. **Configure AWS** (optional): Set up credentials for live testing
3. **Integrate with MCP Client**: Connect from Claude Desktop or other clients
4. **Production Setup**: Configure with real S3 Tables resources

The server is designed to work in both development (mock) and production (AWS) environments.

## Supported Operations

- [X] CreateNamespace: Prompt: `Create a namespaces in the s3-table-bucket with s3_namespace name`
- [X] CreateTable: Prompt: `Create a table in the test_namespace with test-table name` 
- [X] CreateTableBucket: Prompt: `Create an s3 table bucket with s3-table-bucket name` 
- [X] DeleteNamespace: Prompt: `Delete the test_namespace`
- [X] DeleteTable: Prompt: `Delete the test_table`
- [X] DeleteTableBucket: Prompt: `Delete the s3-table-bucket`
- [X] DeleteTableBucketEncryption: Prompt: `Delete table bucket encryption of s3-table-bucket`
- [X] DeleteTableBucketPolicy: Prompt: `Delete table bucket policy of s3-table-bucket`
- [X] DeleteTablePolicy: Prompt: `Delete table policy of test_table`
- [X] GetNamespace: Prompt: `Get information about test_namespace`
- [X] GetTable: Prompt: `Get information about test_table`
- [X] GetTableBucket: Prompt: `Get information about s3-table-bucket`
- [X] GetTableBucketEncryption: Prompt: `Get table bucket encryption of s3-table-bucket`
- [X] GetTableBucketMaintenanceConfiguration: Prompt: `Get table bucket maintenance config of s3-table-bucket`
- [X] GetTableBucketPolicy: Prompt: `Get table bucket policy of s3-table-bucket`
- [X] GetTableEncryption: Prompt: `Get encryption configuration of test_table`
- [X] GetTableMaintenanceConfiguration: Prompt: `Get maintenance configuration of test_table`
- [X] GetTableMaintenanceJobStatus: Prompt: `Get maintenance job status of test_table`
- [X] GetTableMetadataLocation: Prompt `Get table metadata location of test_table`
- [X] GetTablePolicy: Prompt: `Get table policy of test_table`
- [X] ListNamespaces: Prompt: `List all s3 table bucket namespaces`
- [X] ListTableBuckets: Prompt: `List all s3 table buckets`
- [X] ListTables: Prompt: `List all s3 tables`
- [X] PutTableBucketEncryption: Prompt: `Configure bucket encryption for the s3-table-bucket`
- [X] PutTableBucketMaintenanceConfiguration: Prompt: `Configure maintanence for the s3-table-bucket`
- [ ] PutTableBucketPolicy TODO: LLM cannot parse the json string
- [X] PutTableMaintenanceConfiguration: Prompt: `Put table maintenance configuration for test_table_1`
- [ ] PutTablePolicy TODO: LLM cannot parse the json string
- [X] RenameTable: Prompt: `Rename test_table_1 to llm_table_1`
- [X] UpdateTableMetadataLocation: Prompt: `Update metadata location to new_location.metadata.json for test_table_1`
