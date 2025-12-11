---
name: "amazon-aurora-postgresql"
displayName: "Build applications with Aurora PostgreSQL"
description: "Build applications backed by Aurora PostgreSQL by leveraging this power. It bundles direct database connectivity through the Aurora PostgreSQL MCP server for data plane operations (queries, table creation, schema management), and control plane operations (cluster creation), The steering file helps with Aurora PostgreSQL specific best practices. When developers work on database tasks, the power dynamically loads relevant guidance - whether creating new Aurora clusters, designing schemas, or optimizing queries - so Kiro agent receives only the context needed for the specific task at hand."
keywords: ["aurora", "postgresql", "aurora-postgresql", "amazon", "serverless", "rds-postgresql", "postgres", "AWSforData", "Analytics", "database", "aws", "rds"]
author: "AWS"
---

# Aurora Postgres Power

## Overview

Build database-backed applications with Aurora PostgreSQL through seamless MCP server integration. This power provides:

- Data Plane Operations: Execute queries, create tables, and manage schemas through direct database connectivity
- Control Plane Operations: Create and manage Aurora clusters programmatically
- Context-Aware Guidance: The steering file dynamically loads Aurora PostgreSQL best practices relevant to your current task—whether designing schemas, optimizing queries, or provisioning clusters—ensuring Kiro receives only the context it needs
This power combines comprehensive guidance for database design, query optimization, schema management, and operational excellence with direct MCP integration for both provisioned instances and Aurora Serverless v2

## Available Steering Files

This power includes two comprehensive steering files that provide detailed guidance:

- **aurora-postgres-mcp** - MCP server usage patterns, tool policies, and SQL style guide for working with the Aurora Postgres MCP server
- **aurora-postgres** - Complete development guide covering schema design, indexing strategies, query optimization, migrations, monitoring, and operational best practices

Call action "readSteering" to access specific guides as needed.

## MCP Server Integration

This power uses the **awslabs.postgres-mcp-server** MCP server to provide direct integration with Aurora PostgreSQL clusters.

### Available Tools

The MCP server provides tools for:
- **Cluster Management**: Create clusters, monitor job status
   -- database cluster creation take about 5 to 10 minutes after create_cluster tool call
   -- get_job_status tool should be run every minute or so. Running it every few seconds is excessive and may feel like a stuck loop.
- **Database Connections**: Connect to databases, manage multiple connections
- **Query Execution**: Run SQL queries with safety guardrails
- **Schema Exploration**: Get table schemas and metadata

### Connection Management

**Connecting to a Database:**
```
Call mcp_postgres_connect_to_database with:
- database_type: "APG" (Aurora Postgres) or "RPG" (RDS Postgres)
- connection_method: "rdsapi", "pgwire", or "pgwire_iam"
- cluster_identifier: your cluster name
- db_endpoint: database instance endpoint, not needed when connection_method is rdsapi
- database: database name
- port: 5432
- region: AWS region
```

**Checking Active Connections:**
```
Call mcp_postgres_get_database_connection_info to see all active connections
```

### Query Execution

**Running Queries:**
```
Call mcp_postgres_run_query using results from mcp_postgres_connect_to_database call
Call mcp_postgres_run_query with:
- connection_method: same as connection
- cluster_identifier: your cluster
- db_endpoint: cluster endpoint
- database: database name
- sql: your SQL query
- query_parameters: optional parameters array
```

**Safety Guidelines:**
- Read-only by default - writes requires adding "--allow_write_query" to mcp.json and "RUN IT"
- Always use LIMIT on browsing queries
- Run EXPLAIN plans before heavy queries
- Bound queries with WHERE predicates
-

## Common Workflows

### Workflow 1: Create and Connect to Cluster

**Goal:** Set up a new Aurora Postgres cluster and establish connection

**Steps:**
1. Create cluster asynchronously:
   ```
   Call mcp_postgres_create_cluster with region and cluster_identifier
   Returns job_id for monitoring
   ```

2. Monitor cluster creation:
   ```
   Call mcp_postgres_get_job_status with job_id
   Poll every 30-60 seconds until COMPLETED
   ```

3. Connect to the cluster:
   ```
   Call mcp_postgres_connect_to_database with cluster details
   ```

4. Create your application database:
   ```
   Call mcp_postgres_run_query with:
   sql: "CREATE DATABASE myapp;"
   ```

### Workflow 2: Schema Exploration

**Goal:** Understand existing database structure

**Steps:**
1. List all tables:
   ```sql
   SELECT schemaname, tablename,
     pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
   FROM pg_tables
   WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
   ORDER BY schemaname, tablename;
   ```

2. Get table schema:
   ```
   Call mcp_postgres_get_table_schema with table_name
   ```

3. Check indexes:
   ```sql
   SELECT schemaname, tablename, indexname, idx_scan
   FROM pg_stat_user_indexes
   ORDER BY idx_scan DESC;
   ```

### Workflow 3: Query Optimization

**Goal:** Identify and fix slow queries

**Steps:**
1. Find slow queries via Performance Insights or pg_stat_statements

2. Analyze query plan:
   ```sql
   EXPLAIN (ANALYZE, BUFFERS)
   SELECT ... FROM ... WHERE ...;
   ```

3. Look for issues:
   - Sequential scans on large tables
   - High buffer reads
   - Rows removed by filter

4. Add appropriate indexes:
   ```sql
   CREATE INDEX CONCURRENTLY idx_name
   ON table_name(column1, column2);
   ```

5. Verify improvement with EXPLAIN ANALYZE

### Workflow 4: Safe Schema Migrations

**Goal:** Modify schema without downtime

**Steps:**
1. Check table size and activity:
   ```sql
   SELECT pg_size_pretty(pg_total_relation_size('table_name')),
          n_live_tup FROM pg_stat_user_tables
   WHERE tablename = 'table_name';
   ```

2. Use non-blocking patterns:
   - Add columns: `ALTER TABLE ADD COLUMN` (nullable or with default in PG 11+)
   - Add indexes: `CREATE INDEX CONCURRENTLY`
   - Add constraints: `ADD CONSTRAINT ... NOT VALID` then `VALIDATE CONSTRAINT`

3. Monitor progress for concurrent operations

4. Update statistics after migration:
   ```sql
   VACUUM ANALYZE table_name;
   ```

## Best Practices

### Database Design
- Normalize to 3NF; denormalize only when proven necessary
- Use precise data types (INT over BIGINT, VARCHAR(50) over VARCHAR(255))
- Always define foreign keys and index FK columns
- Use TIMESTAMPTZ for timestamps
- Include created_at/updated_at columns

### Indexing Strategy
- Index all foreign keys (not automatic in PostgreSQL)
- Index WHERE, ORDER BY, GROUP BY, JOIN columns
- Use composite indexes ordered by selectivity
- Create partial indexes for common filters
- Use CONCURRENTLY for production index operations

### Query Development
- Always use WHERE clauses with indexed columns
- Specify column names explicitly (avoid SELECT *)
- Use LIMIT for large result sets
- Batch large INSERT/UPDATE operations
- Wrap multi-statement operations in transactions

### Connection Management
- Use connection pooling (RDS Proxy or app-side)
- Configure appropriate min/max pool sizes
- Set connection timeouts for fast failure
- Use writer endpoint for writes, reader for reads
- For Serverless v2: Always use RDS Proxy

### Monitoring
- Enable Performance Insights
- Configure CloudWatch alarms for key metrics
- Monitor slow query logs
- Track index usage with pg_stat_user_indexes
- Check for table/index bloat regularly

## Troubleshooting

### MCP Connection Issues

**Problem:** Cannot connect to MCP server
**Solutions:**
1. Verify MCP server is installed and running
2. Check mcp.json configuration
3. Ensure AWS credentials are configured
4. Verify network access to Aurora cluster

### Query Performance Issues

**Problem:** Slow query execution
**Diagnostic Steps:**
1. Run EXPLAIN (ANALYZE, BUFFERS) on the query
2. Check for sequential scans on large tables
3. Verify indexes exist on WHERE/JOIN columns
4. Check table statistics are up to date

**Solutions:**
1. Add appropriate indexes using CREATE INDEX CONCURRENTLY
2. Rewrite query to use indexed columns
3. Run VACUUM ANALYZE to update statistics
4. Consider query restructuring or schema changes

### Connection Pool Exhaustion

**Problem:** "Too many connections" errors
**Solutions:**
1. Implement or tune connection pooling
2. Check for connection leaks in application code
3. Consider using RDS Proxy
4. Review and adjust max_connections parameter
5. For Serverless v2: Verify ACU capacity

### Schema Migration Failures

**Problem:** ALTER TABLE locks table or times out
**Solutions:**
1. Use CONCURRENTLY for index operations
2. For constraints: Add NOT VALID, then VALIDATE separately
3. For column type changes: Use shadow column pattern
4. Schedule during low-traffic windows
5. Test on dev cluster first

## Configuration

### MCP Server Setup

The power uses the Aurora Postgres MCP server with the following configuration:

```json
{
  "mcpServers": {
    "postgres": {
      "command": "uvx",
      "args": [
        "awslabs.postgres-mcp-server@latest"
      ]
    }
  }
}
```

**Note:** This configuration uses a local wheel file. You may need to adjust the path to match your installation location.

### Prerequisites

- AWS credentials configured (AWS CLI or environment variables)
- Network access to Aurora PostgreSQL clusters
- Python 3.8+ (for uvx/uv package manager)
- uv installed: https://docs.astral.sh/uv/getting-started/installation/

### Environment Variables

No additional environment variables required. The MCP server uses AWS credentials from your standard AWS configuration.

---

**Package:** awslabs.postgres-mcp-server
**MCP Server:** postgres
