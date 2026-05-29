---
name: "amazon-aurora-mysql"
displayName: "Build applications with Aurora MySQL"
description: "Guide for building applications backed by Aurora MySQL using the Aurora MySQL MCP server. The power supports data plane operations (queries, table creation, schema management) and control plane operations (cluster creation). The bundled steering file loads Aurora MySQL guidance relevant to the current task—creating Aurora clusters, designing schemas, or working with queries—so the Kiro agent receives only the context needed for the task at hand."
keywords: ["aurora", "mysql", "aurora-mysql", "amazon", "serverless", "rds-mysql", "AWSforData", "Analytics", "database", "aws", "rds"]
author: "AWS"
---

# Aurora MySQL Power

## Overview

Build database-backed applications with Aurora MySQL through MCP server integration. This power provides:

- Data Plane Operations: Execute queries, create tables, and manage schemas through direct database connectivity
- Control Plane Operations: Create and manage Aurora clusters programmatically
- Context-Aware Guidance: The steering file loads Aurora MySQL best practices relevant to your current task—designing schemas, optimizing queries, or provisioning clusters—so Kiro receives only the context it needs

This power provides guidance for database design, query optimization, schema management, and operational best practices, with MCP server support for both provisioned instances and Aurora Serverless v2.

## Available Steering Files

This power includes two steering files that provide detailed guidance:

- **aurora-mysql-mcp** - MCP server usage patterns, tool policies, and SQL style guide for working with the Aurora MySQL MCP server
- **aurora-mysql** - Development guide covering schema design, indexing, query development, migrations, monitoring, and operational practices

Call action "readSteering" to access specific guides as needed.

## MCP Server Integration

This power uses the **awslabs.mysql-mcp-server** MCP server to provide direct integration with Aurora MySQL clusters.

### Available Tools

The MCP server provides tools for:
- **Cluster Management**: Create clusters, monitor job status
  -- creates an Aurora MySQL cluster (Serverless v2 by default; provisioned via `cluster_type='provisioned'`) with a single writer instance
  -- `cluster_type` selects the topology: `'serverless_v2'` (auto-scaling 0.5–4 ACU, recommended for variable / bursty / cost-sensitive workloads) or `'provisioned'` (fixed instance class, recommended for steady-state production workloads with predictable load)
  -- `db_instance_class` is `'db.serverless'` (default, for Serverless v2) or a non-serverless class such as `db.r6g.large`, `db.r6g.xlarge`, `db.r7g.large` (for provisioned). The agent SHOULD ask the user to choose between these explicitly when the workload pattern is unclear
  -- cluster creation typically takes 5-7 minutes; poll `get_job_status` every 60 seconds, not every few seconds
  -- Data API (HTTP endpoint) is enabled by default on created clusters
  -- default admin username is `admin`; credentials are managed automatically via Secrets Manager
  -- in accounts without default VPC subnets, pass `db_subnet_group_name` and `vpc_security_group_ids` to avoid `InvalidSubnet` errors
- **Database Connections**: Connect to databases, manage multiple connections
  -- `rdsapi` is the recommended default: works from any host with AWS credentials, no VPC access required
  -- `mysqlwire` uses the MySQL wire protocol with Secrets Manager credentials; requires VPC security group to allow inbound TCP 3306 from your MCP server host
  -- `mysqlwire_iam` uses IAM authentication with strict TLS verification via a bundled Amazon RDS CA; requires IAM authentication enabled on the cluster and a MySQL user configured with `AWSAuthenticationPlugin`
  -- `is_database_connected` checks by `cluster_identifier` alone; you do not need to know which endpoint or database name was used at connect time
  -- run one SQL statement per run_query call; the SQL injection detector rejects stacked queries
- **Query Execution**: Run SQL queries with safety guardrails
- **Schema Exploration**: Get table schemas and metadata from `INFORMATION_SCHEMA`

### Connection Management

**Connecting to a Database:**
```
Call mcp_mysql_connect_to_database with:
- database_type: one of 'aurora-mysql' (Aurora MySQL), 'mysql' (RDS MySQL),
  or 'mariadb' (RDS MariaDB). Self-hosted MySQL/MariaDB does not require this field.
- connection_method: "rdsapi", "mysqlwire", or "mysqlwire_iam"
  -- 'rdsapi' is supported only for aurora-mysql
  -- 'mysqlwire_iam' is supported for aurora-mysql and mysql (RDS MySQL); not for mariadb
  -- 'mysqlwire' is supported for every engine
- cluster_identifier: your cluster name
- db_endpoint: database instance endpoint, not needed when connection_method is rdsapi
- database: database name
- port: 3306
- region: AWS region
```

**Checking Active Connections:**
```
Call mcp_mysql_is_database_connected with:
- cluster_identifier: your cluster name

Call mcp_mysql_get_database_connection_info to list all active connections
```

### Query Execution

**Running Queries:**
```
Call mcp_mysql_run_query using results from mcp_mysql_connect_to_database call
Call mcp_mysql_run_query with:
- connection_method: same as connection
- cluster_identifier: your cluster
- db_endpoint: cluster endpoint
- database: database name
- sql: your SQL query
- query_parameters: optional parameters array
```

**Safety Guidelines:**
- Read-only by default — writes require adding `--allow_write_query` to mcp.json and explicit user confirmation ("RUN IT")
- When writes are enabled, show the SQL and explain its impact before executing
- Always use LIMIT on browsing queries
- Run EXPLAIN ANALYZE plans before heavy queries
- Bound queries with WHERE predicates
- SQL injection detector rejects UNION SELECT, stacked queries, tautologies, SLEEP/BENCHMARK probes, INTO OUTFILE/DUMPFILE, and bare DROP/TRUNCATE/GRANT/REVOKE statements

## Common Workflows

### Workflow 1: Create and Connect to Cluster

**Goal:** Set up a new Aurora MySQL cluster and establish connection

Before invoking the tool, present the user with a choice of cluster topology and instance sizing. Variable / bursty / cost-sensitive workloads → Serverless v2 (default). Steady-state production → provisioned r6g/r7g.

**Steps:**
1. Create cluster asynchronously:
   ```
   # Serverless v2 (default — variable / bursty)
   Call mcp_mysql_create_cluster with region, cluster_identifier

   # Provisioned (steady-state production)
   Call mcp_mysql_create_cluster with region, cluster_identifier,
     cluster_type="provisioned", db_instance_class="db.r6g.large"
   ```

2. Monitor cluster creation:
   ```
   Call mcp_mysql_get_job_status with job_id
   Poll every 60 seconds until status is "succeeded"
   ```

3. Connect to the cluster:
   ```
   Call mcp_mysql_connect_to_database with cluster details
   ```

4. Create your application database:
   ```
   Call mcp_mysql_run_query with:
   sql: "CREATE DATABASE myapp;"
   ```

### Workflow 2: Schema Exploration

**Goal:** Understand existing database structure

**Steps:**
1. List all tables with sizes:
   ```sql
   SELECT TABLE_SCHEMA, TABLE_NAME,
     ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) AS size_mb
   FROM INFORMATION_SCHEMA.TABLES
   WHERE TABLE_SCHEMA NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
   ORDER BY TABLE_SCHEMA, TABLE_NAME;
   ```

2. Get table schema:
   ```
   Call mcp_mysql_get_table_schema with table_name
   ```

3. Check indexes:
   ```sql
   SELECT TABLE_SCHEMA, TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX, COLUMN_NAME
   FROM INFORMATION_SCHEMA.STATISTICS
   WHERE TABLE_SCHEMA NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
   ORDER BY TABLE_SCHEMA, TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;
   ```

### Workflow 3: Query Optimization

**Goal:** Identify and fix slow queries

**Steps:**
1. Find slow queries via Performance Insights or the slow query log

2. Analyze query plan:
   ```sql
   EXPLAIN ANALYZE
   SELECT ... FROM ... WHERE ...;
   ```

3. Look for issues:
   - Full table scans on large tables
   - High rows examined vs rows returned
   - Filesort or temporary table usage

4. Add appropriate indexes (online DDL, no table lock):
   ```sql
   ALTER TABLE table_name ADD INDEX idx_name (column1, column2)
   ALGORITHM=INPLACE, LOCK=NONE;
   ```

5. Verify improvement with EXPLAIN ANALYZE

### Workflow 4: Safe Schema Migrations

**Goal:** Modify schema without downtime

**Steps:**
1. Check table size and activity:
   ```sql
   SELECT TABLE_NAME,
     ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) AS size_mb,
     TABLE_ROWS
   FROM INFORMATION_SCHEMA.TABLES
   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'your_table';
   ```

2. Use non-blocking patterns:
   - Add columns: `ALTER TABLE ADD COLUMN` (instant for nullable in MySQL 8.0+)
   - Add indexes: `ALTER TABLE ... ADD INDEX ... ALGORITHM=INPLACE, LOCK=NONE`
   - Online DDL for most operations

3. Monitor progress for long-running DDL

4. Update statistics after migration:
   ```sql
   ANALYZE TABLE table_name;
   ```

### Workflow 5: Migrate from RDS MySQL to Aurora MySQL

**Goal:** Move an existing RDS MySQL workload to Aurora MySQL with minimal downtime

**Migration Safety Rules (MUST follow)**

1. The source RDS instance MUST remain fully operational and serving production traffic during Aurora read replica creation and replication sync. The agent MUST NOT stop, modify, reboot, or redirect traffic from the source application until ALL of the following are true:
   - The Aurora read replica cluster is `available`
   - The Aurora writer instance is `available`
   - `AuroraBinlogReplicaLag` is observed at 0 seconds for **two consecutive 1-minute CloudWatch samples** (a single 0 reading right after the writer comes up can be the metric not yet populated, not actual catch-up)
   - The user has explicitly confirmed promotion can proceed
2. The agent MUST emit a written cutover plan listing every remaining action with timestamps before any traffic-affecting step. The plan MUST distinguish steps that affect application traffic from steps that do not.
3. Application downtime is ONLY acceptable during the promotion step itself (`promote-read-replica-db-cluster` invocation through application repointing).
4. The agent MUST NOT modify the source RDS instance's master credentials, parameter group, or storage settings during migration unless the assessment surfaced an incompatibility AND the user explicitly authorized the change.

**Paths:**
- **Snapshot restore** — simpler, downtime measured in minutes. Best for small databases and tolerated maintenance windows.
- **Read-replica promotion** — near-zero downtime (seconds). Recommended default for online workloads. Requires same MySQL major version on source and target.

**Connection cheat sheet:**
- Source (RDS MySQL) — `database_type: 'mysql'` + `mysqlwire` connection method. Data API is Aurora-only. MCP reads the source for row-count and schema verification only.
- Target (Aurora MySQL) — `database_type: 'aurora-mysql'` + `rdsapi`. All writes land here.

**Steps (read-replica promotion path):**
1. Run the pre-migration assessment. The agent **MUST NOT** proceed to step 2 until **BOTH** conditions below are met:
   - **(a)** Check 1 (Engine version) returns ✓ — source community version is at or below the latest Aurora target's community base — **OR** returns ⚠ AND the user has explicitly accepted the version gap and chosen one of two recovery options (wait for next Aurora release, or proceed at the older Aurora patch). RDS source downgrade is **NOT** offered as an option — RDS MySQL does not support in-place minor-version downgrades.

     **AND**

   - **(b)** Check 5 (Master credential mode) returns ✓ — **OR** returns ⚠ AND the user has authorized one of the recovery options (pre-stage fixed password or fall back to Path 1 / snapshot restore).
2. Enable binlog retention on the RDS source (168 hours recommended)
3. Create the Aurora read replica via `aws rds create-db-cluster --replication-source-identifier`
4. Add an Aurora writer instance
5. Monitor `AuroraBinlogReplicaLag` until it reads 0 for **two consecutive 1-minute CloudWatch samples**
6. Emit a written cutover plan; obtain explicit user confirmation
7. **Traffic-affecting:** quiesce application writes, verify lag is 0, promote with `aws rds promote-read-replica-db-cluster`
8. **Traffic-affecting:** repoint application to the Aurora writer endpoint
9. Run the post-migration validation workflow and emit the `Migration validation: ✓/⚠/✗` block

See the `aurora-mysql` steering file under "Migration: RDS MySQL to Aurora MySQL" for the full Migration Safety Rules text, snapshot-restore steps, version compatibility matrix, cutover checklists, and rollback plans.

### Workflow 6: Set Up Aurora MySQL Replication

**Goal:** Scale reads, add cross-region resilience, or stream changes to downstream consumers

**Paths:**
- **In-region Aurora read replicas** — up to 15 replicas per cluster; < 20 ms lag; use the reader endpoint to load-balance reads
- **Aurora Global Database** — cross-region replicas; storage-level replication with < 1 s lag; managed planned failover
- **Binlog replication to external consumers** — enable binlog on Aurora, create a replication user, and point any MySQL-protocol consumer at the cluster with `CHANGE REPLICATION SOURCE TO`. Consumer-side configuration is outside this power's scope.

**Monitoring:**
- `AuroraReplicaLag` for in-region replicas
- `AuroraGlobalDBReplicationLag` and `AuroraGlobalDBRPOLag` for Global Database
- `AuroraBinlogReplicaLag` for binlog consumers
- `SHOW REPLICA STATUS\G` on external consumers

See the `aurora-mysql` steering file under "Replication: Read Replicas, Global Database, Binlog" for step-by-step setup, parameter changes, and CloudWatch alarm thresholds.

## Best Practices

### Database Design
- Use InnoDB engine for all tables (default in Aurora MySQL)
- Normalize to 3NF; denormalize only when proven necessary
- Use precise data types (INT over BIGINT, VARCHAR(50) over VARCHAR(255))
- Always define foreign keys and index FK columns
- Use DATETIME or TIMESTAMP for timestamps
- Include created_at/updated_at columns with ON UPDATE CURRENT_TIMESTAMP

### Indexing Strategy
- Index all foreign keys
- Index WHERE, ORDER BY, GROUP BY, JOIN columns
- Use composite indexes ordered by selectivity (most selective first)
- Use covering indexes to avoid table lookups
- Use prefix indexes for long string columns
- Use ALGORITHM=INPLACE, LOCK=NONE for production index operations

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
- Track index usage with INFORMATION_SCHEMA.STATISTICS
- Check for table fragmentation regularly

## Troubleshooting

### MCP Connection Issues

**Problem:** Cannot connect to MCP server
**Solutions:**
1. Verify MCP server is installed and running
2. Check mcp.json configuration
3. Ensure AWS credentials are configured
4. Verify network access to Aurora cluster

**Problem:** `mysqlwire_iam` fails with `CERTIFICATE_VERIFY_FAILED`
**Solutions:**
1. Upgrade to the latest `awslabs.mysql-mcp-server` — it ships with a bundled Amazon RDS CA bundle
2. If AWS has rotated the CA bundle since your package version, pass `--ca_bundle <path>` with a fresh PEM downloaded from https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem

### Query Performance Issues

**Problem:** Slow query execution
**Diagnostic Steps:**
1. Run EXPLAIN ANALYZE on the query
2. Check for full table scans on large tables
3. Verify indexes exist on WHERE/JOIN columns
4. Check table statistics are up to date

**Solutions:**
1. Add appropriate indexes using online DDL
2. Rewrite query to use indexed columns
3. Run ANALYZE TABLE to update statistics
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
1. Use ALGORITHM=INPLACE, LOCK=NONE for online DDL
2. For large tables: consider pt-online-schema-change
3. Schedule during low-traffic windows
4. Test on dev cluster first

### Cluster Creation Fails in Custom VPCs

**Problem:** `create_cluster` fails with `InvalidSubnet: No default subnet detected in VPC`
**Solutions:**
1. Pass `db_subnet_group_name` to `create_cluster` with your existing DB subnet group name
2. Optionally pass `vpc_security_group_ids` to attach specific security groups
3. Without these, RDS tries to auto-discover default subnets, which only works in accounts that have them

## Configuration

### MCP Server Setup

The power uses the Aurora MySQL MCP server with the following configuration:

```json
{
  "mcpServers": {
    "awslabs.mysql-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.mysql-mcp-server@latest"
      ]
    }
  }
}
```

To enable write queries, add `--allow_write_query` to the `args` array.

### Prerequisites

- AWS credentials configured (AWS CLI or environment variables)
- Network access to Aurora MySQL clusters (only required for `mysqlwire` and `mysqlwire_iam`)
- Python 3.10+ (for uvx/uv package manager)
- uv installed: https://docs.astral.sh/uv/getting-started/installation/

### Environment Variables

No additional environment variables required. The MCP server uses AWS credentials from your standard AWS configuration.

## License

This power integrates with awslabs.mysql-mcp-server (Apache-2.0 license).

## Privacy

The Aurora MySQL Power uses your locally configured AWS credentials to connect to your Aurora MySQL clusters. Your AWS IAM credentials remain on your local machine and are used solely for accessing AWS services. No client-side telemetry is collected by this power. Database queries are executed directly against your clusters and are not logged or transmitted externally.

---

**Package:** awslabs.mysql-mcp-server
**MCP Server:** mysql
