# PostgreSQL MCP Server

An AWS Labs Model Context Protocol (MCP) server (StreamableHTTP) for PostgreSQL databases.

## Natural Language to PostgreSQL SQL Query

Converting human-readable questions and commands into structured PostgreSQL-compatible SQL queries and executing them against the configured PostgreSQL database.

## Overview

This MCP server provides tools for interacting with PostgreSQL databases, including:

1. **Running SQL queries** with injection protection
2. **Analyzing database structure** (schemas, tables, indexes)
3. **Analyzing query performance** with EXPLAIN plans
4. **Recommending indexes** based on table statistics
5. **Executing read-only queries** with security validation
6. **Analyzing table fragmentation** and bloat
7. **Analyzing vacuum statistics** and maintenance needs
8. **Identifying slow-running queries** (requires pg_stat_statements)
9. **Viewing PostgreSQL configuration settings** with filtering
10. **Health checking** server and database connectivity

## Connection Options

The server supports multiple connection methods:

### 1. Direct PostgreSQL Connection (Recommended)

- `hostname`: Database hostname or IP address
- `port`: Database port (default: 5432)
- `secret_arn`: ARN of the secret in AWS Secrets Manager containing credentials
- `database`: Database name to connect to
- `region`: AWS region where the secret is stored
- `readonly`: Enforce read-only operations (recommended: "true")

**Usage:**
```bash
python -m awslabs.postgres_mcp_server.server \
  --hostname "[your-db-host.amazonaws.com]" \
  --port 5432 \
  --secret_arn "[your data]" \  # pragma: allowlist secret
  --database "[your database name]" \
  --region "[your data]" \
  --readonly "true"
```

### 2. AWS RDS Data API (Aurora Postgres) 

- `resource_arn`: ARN of the RDS cluster or instance
- `secret_arn`: ARN of the secret in AWS Secrets Manager containing credentials 
- `database`: Database name to connect to
- `region`: AWS region where the resources are located
- `readonly`: Enforce read-only operations (recommended: "true")

**Usage:**
```bash
python -m awslabs.postgres_mcp_server.server \
  --resource_arn "[your data]" \
  --secret_arn "[your data]" \  
  --database "[your database name]" \
  --region "[your data]" \
  --readonly "true"
```

**Note:** Both connection methods are fully integrated and functional. The server automatically determines the connection type based on the parameters provided.

## Prerequisites

1. Install Python using `uv python install 3.10`
2. PostgreSQL database with username and password stored in AWS Secrets Manager
3. Enable RDS Data API for your RDS PostgreSQL instance/cluster, see [instructions here](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api.html)
4. This MCP server can be run locally on the same host as your LLM client or remotely (ECS, EKS etc.)
5. Docker runtime 
6. Set up AWS credentials with access to AWS services
    - You need an AWS account with appropriate permissions
    - Configure AWS credentials with `aws configure` or environment variables

## Required PostgreSQL Extensions

For full functionality, the following PostgreSQL extensions should be enabled:

- `pg_stat_statements`: Required for the `get_slow_queries` tool
  ```sql
  CREATE EXTENSION pg_stat_statements;
  ```
  
  For RDS instances, you need to:
  1. Create a parameter group with `shared_preload_libraries = 'pg_stat_statements'`
  2. Associate the parameter group with your RDS instance
  3. Restart the instance
  4. Run `CREATE EXTENSION pg_stat_statements;`

## Connection Pool

The server implements a connection pool for PostgreSQL connections to improve performance and resource utilization. The connection pool:

- Maintains a minimum number of database connections
- Limits the maximum number of concurrent connections
- Reuses connections across sessions
- Automatically handles connection lifecycle

### Connection Pool Configuration

You can configure the connection pool using environment variables:

- `POSTGRES_POOL_MIN_SIZE`: Minimum number of connections to keep in the pool (default: 5)
- `POSTGRES_POOL_MAX_SIZE`: Maximum number of connections allowed in the pool (default: 30)

## Running the Server

### Method 1: Navigate to Project Directory (Recommended)

```bash
# Clone and navigate to the project
git clone https://github.com/your-repo/aws-mcp-servers.git
cd aws-mcp-servers/src/postgres-mcp-server

# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .

# Set AWS credentials
export AWS_PROFILE=your-profile-name
export AWS_REGION=us-west-2

# Run the server
python -m awslabs.postgres_mcp_server.server \
  --resource_arn "[your data]" \
  --secret_arn "[your data]" \  
  --database "[your database name]" \
  --region "[your data]" \
  --readonly "true"
```

### Method 2: Install in Development Mode (For Remote Hosts)

```bash
# Navigate to the postgres-mcp-server directory
cd /path/to/aws-mcp-servers/src/postgres-mcp-server

# Install in development mode (makes module available system-wide)
pip install -e .

# Now you can run from any directory
python -m awslabs.postgres_mcp_server.server \
  --resource_arn "[your data]" \
  --secret_arn "[your data]" \  
  --database "[your database name]" \
  --region "[your data]" \
  --readonly "true"
```

### Method 3: Using PYTHONPATH (Alternative)

```bash
# From any directory, set PYTHONPATH to include the postgres-mcp-server directory
export PYTHONPATH=/path/to/aws-mcp-servers/src/postgres-mcp-server:$PYTHONPATH

# Run the server
python -m awslabs.postgres_mcp_server.server \
  --resource_arn "[your data]" \
  --secret_arn "[your data]" \  
  --database "[your database name]" \
  --region "[your data]" \
  --readonly "true"
```

### Troubleshooting Common Issues

#### Issue: "ModuleNotFoundError: No module named 'postgres_mcp_server'"

**Problem:** Wrong module path or not in correct directory.

**Solutions:**
1. **Use correct module path:** `awslabs.postgres_mcp_server.server` (not `postgres_mcp_server.server`)
2. **Navigate to correct directory:** `cd /path/to/aws-mcp-servers/src/postgres-mcp-server`
3. **Set PYTHONPATH:** `export PYTHONPATH=/path/to/postgres-mcp-server:$PYTHONPATH`
4. **Install in development mode:** `pip install -e .`

#### Issue: "No such file or directory: requirements.txt"

**Problem:** Missing requirements.txt file.

**Solution:** Use the requirements.txt file included in the repository, or install from pyproject.toml:
```bash
pip install -e .
```

#### Issue: AWS credentials not found

**Problem:** AWS credentials not configured properly.

**Solutions:**
1. **Set AWS profile:** `export AWS_PROFILE=your-profile-name`
2. **Configure AWS CLI:** `aws configure`
3. **Use IAM roles** (for EC2/ECS deployments)

### Using Docker (Recommended - Secure Credential Management)

#### Option 1: AWS Credential File Mount (Recommended)
```bash
cd postgres-mcp-server
docker build -t postgres-mcp-server .

# Mount AWS credentials from host
docker run -p 8000:8000 \
  -v ~/.aws:/root/.aws:ro \
  -e AWS_PROFILE=your-profile-name \
  postgres-mcp-server
```

#### Option 2: IAM Roles (Production Recommended)
```bash
# For ECS/EKS deployments - use IAM roles for service accounts
# No credential mounting needed - AWS SDK automatically uses IAM role

docker run -p 8000:8000 \
  postgres-mcp-server
```

#### Option 3: AWS SSO/CLI Integration
```bash
# After running 'aws sso login' on host
docker run -p 8000:8000 \
  -v ~/.aws:/root/.aws:ro \
  -e AWS_PROFILE=[your-sso-profile] \
  postgres-mcp-server
```

####  **SECURITY WARNING - DO NOT USE IN PRODUCTION**
```bash
#  INSECURE - Never hardcode credentials in Docker commands
#  This exposes credentials in process lists and Docker history
docker run -p 8000:8000 \
  -e AWS_ACCESS_KEY_ID=[your data] \  
  -e AWS_SECRET_ACCESS_KEY=[your data] \  
  postgres-mcp-server
```

## Amazon Q Developer CLI Integration

Configure the PostgreSQL MCP Server with Amazon Q Developer CLI by adding to your MCP configuration file (`~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "postgresql-enhanced": {
      "command": "python",
      "args": [
        "-m",
        "awslabs.postgres_mcp_server.server",
        "--resource_arn", "[your data]",
        "--secret_arn", "[your data]",  
        "--database", "[your database name]",
        "--region", "[your data]",
        "--readonly", "true"
      ],
      "cwd": "/path/to/postgres-mcp-server",
      "env": {
        "AWS_PROFILE": "your-profile-name",
        "AWS_REGION": "[your data]",
        "PYTHONPATH": "/path/to/postgres-mcp-server"
      },
      "timeout": 30000,
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Security Best Practices for Q Chat Integration

####  **Recommended: Use AWS Profiles**
```json
{
  "env": {
    "AWS_PROFILE": "your-profile-name",
    "AWS_REGION": "your data"
  }
}
```

####  **NOT Recommended: Hardcoded Credentials**
```json
{
  "env": {
    "AWS_ACCESS_KEY_ID": "[your data]",  
    "AWS_SECRET_ACCESS_KEY": "[your data]",  
    "AWS_SESSION_TOKEN": "[your data]"  
  }
}
```

## Security

### AWS Credential Management

This server uses AWS RDS Data API and requires proper AWS credentials. **Never hardcode credentials in configuration files or Docker commands.**

####  **Recommended Approaches:**

1. **AWS Profiles** (Local Development)
   ```bash
   export AWS_PROFILE=your-profile-name
   ```

2. **IAM Roles** (Production - ECS/EKS)
   - Use IAM roles for service accounts
   - No credential management needed

3. **AWS SSO** (Enterprise)
   ```bash
   aws sso login --profile your-sso-profile
   export AWS_PROFILE=your-sso-profile
   ```

####  **Security Anti-Patterns to Avoid:**

1. **Hardcoded Credentials in Docker**
   ```bash
   #  NEVER DO THIS
   docker run -e AWS_ACCESS_KEY_ID=[your data] -e AWS_SECRET_ACCESS_KEY=[your data]  
   ```

2. **Credentials in Configuration Files**
   ```json
   //  NEVER DO THIS
   {
     "env": {
       "AWS_ACCESS_KEY_ID": "[your data]", 
       "AWS_SECRET_ACCESS_KEY": "[your data]" 
     }
   }
   ```

3. **Credentials in Environment Variables (Production)**
   ```bash
   #  AVOID IN PRODUCTION
   export AWS_ACCESS_KEY_ID=[your data]
   export AWS_SECRET_ACCESS_KEY=[your data]
   ```

### Database Security

All operations are performed in read-only mode for security reasons. The server includes:

1. **SQL injection protection** - Query validation and sanitization
2. **Read-only enforcement** - Validation of mutating SQL keywords
3. **Connection security** - Uses AWS RDS Data API with IAM authentication

## Tools

The PostgreSQL MCP Server provides 10 comprehensive tools for database analysis and management:

### Core Database Tools (3)

#### connect_database
Connect to a PostgreSQL database and store the connection in the session.
```
connect_database(
    secret_name: str = None, 
    region_name: str = "us-west-2",
    secret_arn: str = None, 
    resource_arn: str = None, 
    database: str = None,
    readonly: bool = True
) -> str
```

#### run_query
Run a SQL query against a PostgreSQL database with injection protection.
```
run_query(sql: str) -> list[dict]
```

#### get_table_schema
Fetch table schema from the PostgreSQL database.
```
get_table_schema(table_name: str, database_name: str) -> list[dict]
```

#### health_check
Check if the server is running and responsive.
```
health_check() -> Dict[str, Any]
```

### Database Analysis Tools (7)

#### analyze_database_structure
Analyze the database structure and provide insights on schema design, indexes, and potential optimizations.
```
analyze_database_structure(debug: bool = False) -> str
```

#### show_postgresql_settings
Show PostgreSQL configuration settings with optional filtering.
```
show_postgresql_settings(
    pattern: str = None,
    debug: bool = False
) -> str
```

#### identify_slow_queries
Identify slow-running queries in the database (requires pg_stat_statements extension).
```
identify_slow_queries(
    min_execution_time: float = 100.0,
    limit: int = 20,
    debug: bool = False
) -> str
```

#### analyze_table_fragmentation
Analyze table fragmentation and provide optimization recommendations.
```
analyze_table_fragmentation(
    threshold: float = 10.0,
    debug: bool = False
) -> str
```

#### analyze_query_performance
Analyze a SQL query and provide optimization recommendations.
```
analyze_query_performance(
    query: str,
    debug: bool = False
) -> str
```

#### analyze_vacuum_stats
Analyze vacuum statistics and provide recommendations for vacuum settings.
```
analyze_vacuum_stats(debug: bool = False) -> str
```

#### recommend_indexes
Recommend indexes for database optimization based on query patterns.
```
recommend_indexes(
    query: str = None,
    debug: bool = False
) -> str
```

## Dependencies

- boto3
- botocore
- loguru
- mcp[cli]
- pydantic
- psycopg2-binary
- starlette
- uvicorn

## Testing

The server includes a comprehensive test suite to validate all functionality:

```bash
# Run comprehensive test suite (all 10 tools)
python tests/test_all_tools_comprehensive.py

# Run type conversion validation
python tests/test_type_conversions.py
```

For detailed testing information, see [TESTING.md](TESTING.md).

## Development and Testing

### Setting Up Development Environment

```bash
cd postgres-mcp-server
python3.10 -m venv .venv
source .venv/bin/activate
python3.10 -m pip install -e .
```

### Running Tests

Run all tests:
```bash
python -m pytest tests/
```

Run tests with coverage:
```bash
python -m pytest tests/ --cov=awslabs.postgresql_mcp_server --cov-report=term --cov-report=html
```

Run specific test files:
```bash
python -m pytest tests/test_server.py
python -m pytest tests/test_tools.py
```

### Integration Tests

To run integration tests, set the following environment variables:
```bash
export POSTGRES_MCP_TEST_RESOURCE_ARN="your-resource-arn"
export POSTGRES_MCP_TEST_SECRET_ARN="your-secret-arn"  # pragma: allowlist secret
export POSTGRES_MCP_TEST_DATABASE="your-database"
export POSTGRES_MCP_TEST_REGION="your-region"
python -m pytest tests/test_integration.py -v
```
