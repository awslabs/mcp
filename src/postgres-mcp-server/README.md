# PostgreSQL MCP Server

An AWS Labs Model Context Protocol (MCP) server for PostgreSQL databases with comprehensive analysis capabilities.

## Overview

This MCP server provides 10 tools for PostgreSQL database interaction and analysis:

**Core Tools:**
- `run_query` - Execute SQL queries with injection protection
- `get_table_schema` - Fetch table schema information
- `health_check` - Check server and database connectivity
- `analyze_database_structure` - Analyze schemas, tables, and indexes

**Analysis Tools:**
- `show_postgresql_settings` - View PostgreSQL configuration
- `identify_slow_queries` - Find slow-running queries (requires pg_stat_statements)
- `analyze_table_fragmentation` - Analyze table bloat and fragmentation
- `analyze_query_performance` - Query optimization with EXPLAIN plans
- `analyze_vacuum_stats` - Vacuum statistics and maintenance recommendations
- `recommend_indexes` - Index recommendations based on query patterns

## Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL database with credentials in AWS Secrets Manager
- AWS credentials configured (profiles recommended)
- `uv` package manager ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))

### Installation
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone <repository>
cd src/postgres-mcp-server

# Basic installation (RDS Data API only)
uv sync

# Full installation with direct PostgreSQL support
uv sync --extra postgres
```

### Running the Server

#### Method 1: RDS Data API (Aurora PostgreSQL)
```bash
uv run python -m awslabs.postgres_mcp_server.server \
  --resource_arn "arn:aws:rds:region:account:cluster:cluster-name" \
  --secret_arn "arn:aws:secretsmanager:region:account:secret:name" \
  --database "your-database-name" \
  --region "us-west-2" \
  --readonly "true"
```

#### Method 2: Direct PostgreSQL Connection
```bash
uv run python -m awslabs.postgres_mcp_server.server \
  --hostname "your-db-host.amazonaws.com" \
  --port 5432 \
  --secret_arn "arn:aws:secretsmanager:region:account:secret:name" \
  --database "your-database-name" \
  --region "us-west-2" \
  --readonly "true"
```

#### Method 3: Docker
```bash
docker build -t postgres-mcp-server .
docker run -p 8000:8000 \
  -v ~/.aws:/root/.aws:ro \
  -e AWS_PROFILE=your-profile-name \
  postgres-mcp-server \
  --resource_arn "your-rds-arn" \
  --secret_arn "your-secret-arn" \
  --database "your-database" \
  --region "us-west-2" \
  --readonly "true"
```

## Testing

```bash
# Run comprehensive test suite
uv run python tests/test_all_tools_comprehensive.py

# Run all tests with pytest
uv run pytest

# Run specific tests
uv run pytest tests/test_connection_pool.py -v
```

**Test Environment Variables:**
For integration tests, set these environment variables:
```bash
export TEST_RESOURCE_ARN="your-rds-cluster-arn"
export TEST_SECRET_ARN="your-secrets-manager-arn"
```

## Amazon Q Developer CLI Integration

Add to your MCP configuration file (`~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "postgresql-enhanced": {
      "command": "uv",
      "args": [
        "run", "python", "-m", "awslabs.postgres_mcp_server.server",
        "--resource_arn", "your-rds-arn",
        "--secret_arn", "your-secret-arn",
        "--database", "your-database",
        "--region", "us-west-2",
        "--readonly", "true"
      ],
      "cwd": "/path/to/postgres-mcp-server",
      "env": {
        "AWS_PROFILE": "your-profile-name"
      }
    }
  }
}
```

## Security Features

- **SQL Injection Protection**: Parameterized queries and validation
- **Read-only Mode**: Enforced readonly operations for safety
- **Credential Security**: AWS profiles only, no hardcoded credentials
- **Query Validation**: Advanced pattern detection and risk assessment

## Development

```bash
# Setup development environment
uv sync --dev

# Run linting
uv run ruff check

# Run formatting
uv run ruff format

# Run type checking
uv run pyright
```

## Configuration

### Connection Pool
Configure via environment variables:
- `POSTGRES_POOL_MIN_SIZE`: Minimum connections (default: 5)
- `POSTGRES_POOL_MAX_SIZE`: Maximum connections (default: 30)

### Required PostgreSQL Extensions
For full functionality, enable:
```sql
CREATE EXTENSION pg_stat_statements;
```

## Documentation

- [Testing Guide](TESTING.md) - Comprehensive testing information

## Dependencies

- boto3, botocore - AWS SDK
- loguru - Logging
- mcp[cli] - Model Context Protocol
- pydantic - Data validation
- psycopg2-binary - PostgreSQL adapter

## License

Apache License 2.0 - See [LICENSE](LICENSE) file for details.
