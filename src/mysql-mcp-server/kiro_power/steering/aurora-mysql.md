---
inclusion: always
---
<!------------------------------------------------------------------------------------
   Add rules to this file or a short description that will apply across all your workspaces.

   Learn about inclusion modes: https://kiro.dev/docs/steering/#inclusion-modes
------------------------------------------------------------------------------------->

# Aurora MySQL Development Guide

Best practices for Aurora MySQL development using MCP server. Covers provisioned instances and Aurora Serverless v2.

## Aurora Serverless v2

**Characteristics:**
- Auto-scales 0.5-128 ACU in seconds (1 ACU = 2 GB RAM)
- Per-second billing, pay only for capacity used
- Use for: variable workloads, dev/test, spiky traffic, multi-tenant SaaS

**Configuration:**
- Dev: min 0.5-1 ACU, prod: min 2-4 ACU
- Set max ACU based on peak load
- Monitor: ServerlessDatabaseCapacity, ACUUtilization metrics
- Always use RDS Proxy for connection pooling
- Test scaling under load before production

## Troubleshooting Sequences

**Slow Queries:**
1. Verify WHERE uses indexed columns
2. Run `EXPLAIN ANALYZE` to identify full table scans
3. Check Performance Insights
4. Update statistics: `ANALYZE TABLE table_name`

**Connection Failures:**
1. Check connection pool config (sizes, timeouts)
2. Verify DNS TTL < 30s
3. Check CloudWatch DatabaseConnections
4. For Serverless v2: verify capacity and RDS Proxy

**Storage Growth:**
1. Query unused indexes (INFORMATION_SCHEMA.STATISTICS)
2. Check fragmentation (INFORMATION_SCHEMA.TABLES)
3. Run OPTIMIZE TABLE for InnoDB defragmentation

**Schema Migrations:**
1. Check if ALTER supports ALGORITHM=INPLACE
2. Use online DDL or pt-online-schema-change
3. Estimate time based on table size
4. Test on dev cluster first

## Cluster Setup

**Initial Config:**
- Create via MCP tool `create_cluster`. **Before invoking, present the user with an explicit choice between `cluster_type='serverless_v2'` (default — variable / bursty / cost-sensitive workloads, auto-scaling 0.5–4 ACU) and `cluster_type='provisioned'` (steady-state production workloads with predictable load, fixed instance class).** Map workload patterns to topologies:
  - Variable / bursty traffic, multi-tenant SaaS, dev/test → `serverless_v2`
  - Steady-state production, predictable load, predictable cost → `provisioned` with `db_instance_class='db.r6g.large'` (or larger / `db.r7g.large`)
  - Memory-bound or analytics-heavy workloads with Optimized Reads → `provisioned` with `db.r6gd.*` / `db.r6id.*`
  - **Avoid burstable t-class** (`db.t3.*`, `db.t4g.*`) for production transactional workloads — CPU credit exhaustion under sustained load is a real failure mode
- MCP tool `create_cluster` returns immediately with job id
- Use MCP tool `get_job_status` with job id to check cluster creation status
- Create MySQL database via MCP tool `run_query`
- Store credentials in Secrets Manager
- Enable Performance Insights and Enhanced Monitoring

**Engine version selection (when starting a new cluster):**

Before presenting an engine-version tradeoff to the user, the agent **MUST** query
```bash
aws rds describe-db-engine-versions \
  --engine aurora-mysql \
  --region <user-region> \
  --query 'DBEngineVersions[].[EngineVersion,DBEngineVersionDescription]' \
  --output json
```
to get the actually-available Aurora MySQL versions in the user's region. Do **NOT** recite a hardcoded list (e.g. "3.07.x LTS / 3.10.x latest") — Aurora ships new minors quarterly and regional availability is not uniform.

Group the results by major version family:
- Aurora MySQL 3 (8.0-compatible)
- Aurora MySQL 8.4 (8.4-compatible, LTS)
- Aurora MySQL 2 (5.7-compatible) — only mention if the source is on MySQL 5.7

Within each major, identify the LTS minor (the `DBEngineVersionDescription` contains the substring "LTS") and the latest non-LTS minor. Present the user with the LTS-vs-latest tradeoff **using the actual versions** AWS reports, with the community base version of each option spelled out so the user can match it to the source.

If Check 1 of the pre-migration assessment matched the source's community version to a specific Aurora target, use that version directly as the recommendation and skip the open-ended LTS-vs-latest question — the assessment already constrained the choice.

**Production Requirements:**
- Multi-AZ deployment
- Backup retention: 7-35 days (default 1 day)
- Encryption: AWS KMS
- DNS TTL < 30s
- RDS Proxy (critical for Serverless v2)

**Instance Types:**
- T: dev/test only (burstable)
- R6g/R6i: general production
- R6gd/R6id: large datasets with Optimized Reads
- X: memory-intensive
- Serverless v2: variable/unpredictable workloads

## Schema Design

**Modeling Process:**
1. Document entity relationships
2. Identify access patterns (read vs write heavy)
3. Estimate data volume and growth
4. Define transaction boundaries

**Design Rules:**
- Use InnoDB engine for all tables
- Normalize to 3NF; denormalize only when proven necessary
- Use precise types: INT over BIGINT, VARCHAR(50) over VARCHAR(255)
- Apply NOT NULL where required
- Use ENUM or CHECK constraints for limited value sets
- Include deleted_at for soft deletes
- Use DATETIME or TIMESTAMP for timestamps

**Keys:**
- Primary: AUTO_INCREMENT INT/BIGINT (default), UUID only when needed
- InnoDB clusters data by primary key — choose wisely
- Foreign: Always define FKs, choose ON DELETE behavior, index all FK columns

## Index Strategy

**Always Index:**
- Primary keys (automatic, also the clustered index in InnoDB)
- Foreign keys
- WHERE, ORDER BY, GROUP BY, JOIN columns

**Index Patterns:**
- Composite: order by selectivity (most selective first), leftmost prefix rule applies
- Covering: include all SELECT columns to avoid table lookups
- Prefix: for long VARCHAR/TEXT columns (`INDEX idx_name (column(20))`)
- No partial indexes in MySQL — use generated columns + index instead

**Never Index:**
- Low-cardinality columns alone (unless in composite)
- Every column (write overhead)
- Redundant indexes (a,b covers a)
- Small tables (< 1000 rows)

**Analysis:**
- `EXPLAIN ANALYZE` for query plans
- Performance Schema for slow queries
- `INFORMATION_SCHEMA.STATISTICS` for index usage

## Query Development

**Never:**
- Full table scans without WHERE on production
- SELECT * in application code
- Unbounded queries without LIMIT
- Deploy without EXPLAIN ANALYZE

**Always:**
- WHERE with indexed columns
- LIMIT for large result sets
- Batch large operations
- Specify column names explicitly

**Write Operations:**
- Batch INSERTs with multi-row VALUES
- Use INSERT ... ON DUPLICATE KEY UPDATE for upserts
- Wrap multi-statement ops in transactions
- Avoid long transactions (blocks purge thread)
- Use LAST_INSERT_ID() for inserted auto-increment values

**Optimization Process:**
1. Find slow queries (Performance Insights, slow_query_log)
2. Run `EXPLAIN ANALYZE`
3. Look for: full table scan, filesort, using temporary
4. Fix: add indexes, rewrite query, or restructure schema
5. Validate with re-run

## Development Workflow

**Standard Cycle:**
1. Create cluster via MCP
2. Create database: `CREATE DATABASE mydb;`
3. Design schema
4. Create tables and indexes (use online DDL)
5. Develop queries
6. Analyze with `EXPLAIN ANALYZE`
7. Optimize and iterate

**Migrations:**
- Version control all DDL
- Test on dev cluster first
- Maintain rollback scripts
- Use migration tools (Flyway/Liquibase)

## Safe Schema Changes

**InnoDB Online DDL Support (MySQL 8.0+):**

Most ALTER TABLE operations support `ALGORITHM=INPLACE, LOCK=NONE`:
- Adding/dropping indexes
- Adding columns (at end of table)
- Changing column default
- Renaming columns/tables
- Adding/dropping foreign keys

**Requires Table Rebuild (ALGORITHM=COPY):**
- Changing column data type
- Changing character set
- Adding primary key to table without one

**Non-Blocking Patterns:**

```sql
-- Add nullable column (instant in MySQL 8.0.12+)
ALTER TABLE users ADD COLUMN last_login DATETIME, ALGORITHM=INSTANT;

-- Add column with default (instant in MySQL 8.0.12+)
ALTER TABLE users ADD COLUMN status VARCHAR(20) DEFAULT 'active', ALGORITHM=INSTANT;

-- Add index without blocking writes
ALTER TABLE users ADD INDEX idx_email (email), ALGORITHM=INPLACE, LOCK=NONE;

-- Drop index without blocking
ALTER TABLE users DROP INDEX idx_old, ALGORITHM=INPLACE, LOCK=NONE;
```

## Safe ALTER Patterns

**Adding NOT NULL Column:**
```sql
-- Multi-step approach
ALTER TABLE users ADD COLUMN phone VARCHAR(20), ALGORITHM=INSTANT;
-- Backfill in batches
UPDATE users SET phone = '' WHERE phone IS NULL AND id BETWEEN 1 AND 10000;
-- Repeat in batches, then:
ALTER TABLE users MODIFY COLUMN phone VARCHAR(20) NOT NULL DEFAULT '';
```

**Changing Column Type:**
```sql
-- Shadow column approach
ALTER TABLE orders ADD COLUMN amount_new DECIMAL(12,2);
-- Backfill in batches
UPDATE orders SET amount_new = amount WHERE amount_new IS NULL LIMIT 10000;
-- Repeat, deploy dual-write code, verify, then swap
ALTER TABLE orders DROP COLUMN amount;
ALTER TABLE orders CHANGE COLUMN amount_new amount DECIMAL(12,2);
```

**For Large Tables — pt-online-schema-change:**
```bash
pt-online-schema-change --alter "ADD COLUMN phone VARCHAR(20)" \
  --host cluster.amazonaws.com --user admin \
  D=mydb,t=users --execute
```

## Migration Workflow

**Pre-Migration:**
```sql
-- Check size and row count
SELECT TABLE_NAME,
  ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) AS size_mb,
  TABLE_ROWS
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users';

-- Check long-running queries
SELECT ID, USER, HOST, DB, TIME, STATE, INFO
FROM INFORMATION_SCHEMA.PROCESSLIST
WHERE TIME > 300 AND COMMAND != 'Sleep';
```

**Execution:**
1. Create snapshot via MCP
2. Test on dev cluster
3. Schedule low-traffic window
4. Monitor Performance Insights
5. Have rollback plan
6. Serverless v2: consider increasing max ACU temporarily

**Post-Migration:**
```sql
ANALYZE TABLE users;  -- Update statistics
SHOW CREATE TABLE users;  -- Verify schema
```

## InnoDB Specifics

**Buffer Pool:**
- Primary cache for data and indexes
- Monitor hit ratio: should be > 99%
- `SHOW ENGINE INNODB STATUS` for detailed info

**Clustered Index:**
- InnoDB stores data ordered by primary key
- Choose PK wisely — sequential (AUTO_INCREMENT) is best for write-heavy
- UUID PKs cause random I/O and page splits

**Purge Thread:**
- Long transactions prevent old row versions from being purged
- Keep transactions short
- Monitor `History list length` in INNODB STATUS

## Finding Missing Indexes

**Using Performance Schema (slow queries):**
```sql
SELECT DIGEST_TEXT, COUNT_STAR, AVG_TIMER_WAIT / 1000000000 AS avg_ms
FROM performance_schema.events_statements_summary_by_digest
WHERE SCHEMA_NAME = DATABASE()
ORDER BY AVG_TIMER_WAIT DESC LIMIT 20;
```

**Full table scans:**
```sql
SELECT TABLE_SCHEMA, TABLE_NAME,
  ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) AS size_mb
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
  AND ENGINE = 'InnoDB'
ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC LIMIT 20;
```

## Unused Indexes

```sql
-- Indexes with zero usage (MySQL 8.0+ with sys schema)
SELECT object_schema, object_name, index_name
FROM performance_schema.table_io_waits_summary_by_index_usage
WHERE index_name IS NOT NULL
  AND count_star = 0
  AND object_schema NOT IN ('mysql', 'performance_schema', 'sys')
ORDER BY object_schema, object_name;
```

## Monitoring

**Performance Insights:**
- Tracks AAS, top SQL, wait events
- Free: 7 days, Paid: up to 2 years

**Slow Query Logging:**
```sql
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;  -- 1 second threshold
```

**CloudWatch Alerts:**
- CPUUtilization > 80%
- DatabaseConnections approaching max
- FreeableMemory low
- ReadLatency/WriteLatency spikes
- BufferCacheHitRatio < 95%
- Serverless v2: ServerlessDatabaseCapacity, ACUUtilization

**InnoDB Status:**
```sql
SHOW ENGINE INNODB STATUS;
-- Key sections: TRANSACTIONS, BUFFER POOL, ROW OPERATIONS
```

**MCP Queries:**
- Table sizes: INFORMATION_SCHEMA.TABLES (DATA_LENGTH + INDEX_LENGTH)
- Index info: INFORMATION_SCHEMA.STATISTICS
- Process list: INFORMATION_SCHEMA.PROCESSLIST
- Connections: SHOW STATUS LIKE 'Threads_connected'

## Connection Examples

**Python (asyncmy):**
```python
import asyncmy
conn = await asyncmy.connect(
    host="cluster.amazonaws.com", port=3306, db="mydb",
    user="admin", password="mypassword"
)
```

**Python with Pool:**
```python
import asyncmy
pool = await asyncmy.create_pool(
    host="cluster.amazonaws.com", port=3306, db="mydb",
    user="admin", password="mypassword",
    minsize=5, maxsize=20
)
```

**Python with IAM Auth:**
```python
import boto3
client = boto3.client('rds')
token = client.generate_db_auth_token(
    DBHostname=ENDPOINT, Port=3306, DBUsername=USER, Region=REGION
)
import asyncmy
conn = await asyncmy.connect(
    host=ENDPOINT, user=USER, password=token, db="mydb",
    ssl=ssl_context
)
```

**Node.js (mysql2):**
```javascript
const mysql = require('mysql2/promise');
const conn = await mysql.createConnection({
  host: 'cluster.amazonaws.com', port: 3306, database: 'mydb',
  user: 'admin', password: 'mypassword', ssl: { rejectUnauthorized: true }
});
```

**Node.js with Pool:**
```javascript
const mysql = require('mysql2/promise');
const pool = mysql.createPool({
  host: 'cluster.amazonaws.com', connectionLimit: 20,
  waitForConnections: true, queueLimit: 0
});
```

**RDS Proxy:** Use proxy endpoint instead of cluster endpoint for auto pooling and failover.

**Connection Checklist:**
1. SSL/TLS: use `ssl` parameter or `require_secure_transport`
2. AWS Advanced Drivers for production (failover)
3. Connection pooling (app-side or RDS Proxy)
4. Timeouts for fast failure
5. IAM auth when possible
6. RDS Proxy for Serverless v2/high-concurrency
7. Writer endpoint for writes, reader for reads
8. DNS TTL < 30s

## Common Patterns

**Well-Designed Table:**
```sql
CREATE TABLE users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    username VARCHAR(50) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    status ENUM('active', 'inactive', 'suspended') DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    UNIQUE KEY uk_email (email),
    UNIQUE KEY uk_username (username),
    INDEX idx_status_created (status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Query Optimization:**
```sql
-- Before: SELECT * FROM orders WHERE customer_id = 123 ORDER BY created_at DESC;

-- Add index
ALTER TABLE orders ADD INDEX idx_customer_created (customer_id, created_at DESC),
  ALGORITHM=INPLACE, LOCK=NONE;

-- Optimize query
SELECT id, order_number, total_amount, created_at
FROM orders WHERE customer_id = 123
ORDER BY created_at DESC LIMIT 50;
```

## Backup and Recovery

**Automated Backups:**
- Continuous to S3, no performance impact
- Default: 1 day (use 7-35 for production)
- Point-in-time recovery within retention
- Multi-AZ storage

**Manual Snapshots:**
- No expiration, create before major deployments
- Shareable across accounts/regions

**Restore:**
- Creates new cluster (not in-place)
- Test before major releases
- Serverless v2: can restore to provisioned or Serverless v2

## Migration: RDS MySQL to Aurora MySQL

Aurora MySQL is a drop-in alternative for RDS MySQL with higher scalability and faster replication. Two supported paths: snapshot restore (simpler, downtime-acceptable) and read-replica promotion (near-zero downtime, recommended default).

### Connection Cheat Sheet for Migrations

The source RDS MySQL cluster is read-only inspected through this MCP. No writes happen against the source.

| Side | `database_type` | Connection method | Why |
|------|-----------------|-------------------|-----|
| Source (RDS MySQL) | `mysql` | `mysqlwire` with Secrets Manager creds | Data API is Aurora-only |
| Source (RDS MySQL with IAM) | `mysql` | `mysqlwire_iam` | If source already has IAM auth enabled |
| Target (Aurora MySQL) | `aurora-mysql` | `rdsapi` (default) | No VPC access required |

Use the MCP on both sides to compare row counts and schema parity during migration. All writes on the target use the Aurora connection.

### Version Compatibility

| Source (RDS MySQL) | Target (Aurora MySQL) | Path |
|--------------------|-----------------------|------|
| MySQL 8.4 | Aurora MySQL 8.4 (8.4-compatible, LTS) | Snapshot restore or read-replica promotion |
| MySQL 8.0 | Aurora MySQL 3 (8.0-compatible) | Snapshot restore or read-replica promotion |
| MySQL 8.0 | Aurora MySQL 8.4 (8.4-compatible) | Major version jump — not supported by native replication. Upgrade RDS MySQL to 8.4 first, then migrate. |
| MySQL 5.7 | Aurora MySQL 3 (8.0-compatible) | Upgrade RDS to 8.0 first, then migrate; major version jumps are not supported by native replication |
| MySQL 5.7 | Aurora MySQL 2 (5.7-compatible) | Snapshot restore or read-replica promotion (note: Aurora MySQL 2 is approaching end of standard support; prefer 8.0 or 8.4) |

**On Aurora MySQL 8.4 versioning:** unlike Aurora MySQL 3 (where the patch level shows up in the customer-visible engine version, e.g. `8.0.mysql_aurora.3.10.4`), Aurora MySQL 8.4+ uses in-place patching within a minor version. Engine versions look like `mysql_aurora.8.4.7` and remain constant across patches. When choosing `--engine-version` in the create-cluster command, use the format AWS surfaces in `aws rds describe-db-engine-versions --engine aurora-mysql`; do not assume the 3.x patch-level convention applies to 8.4.

### Pre-Migration Assessment Workflow

When the user asks for migration help, run the following assessment **before** recommending a path. Connect to the source via `mysqlwire` (`database_type: 'mysql'`) and emit results as a structured checklist that matches this format:

```
Pre-migration assessment for <instance-id>:
✓ / ⚠ / ✗ Engine version: <version> (<compatible|needs upgrade>)
✓ / ⚠ / ✗ Storage engines: <summary>
✓ / ⚠ / ✗ Binary logging: <enabled|disabled> (retention <hours> hours)
✓ / ⚠ / ✗ Parameter compatibility: <N> parameters require adjustment
  - <param>: <current> → <recommended for Aurora>
✓ / ⚠ / ✗ Master credential mode: <managed | fixed-password>

Recommended migration method: <method>
Estimated cutover downtime: <window>
Estimated replication sync time: <duration> for <data size>
```

**Checks to run** (each is one MCP `run_query` call against the source, except Check 1b and Check 5 which use the `aws` CLI):

1. **Engine version** — two-step lookup that compares the source's exact community version against the Aurora targets actually available in the user's region.

   **1a — Source community version:** `SELECT VERSION();` returns the source's exact community version (e.g. `8.0.45`).

   **1b — Available target inventory:** `aws rds describe-db-engine-versions --engine aurora-mysql --region <user-region> --query 'DBEngineVersions[].[EngineVersion,DBEngineVersionDescription]' --output json`. The `DBEngineVersionDescription` field carries the community base version each Aurora release supports, e.g. `"Aurora MySQL 8.0 (compatible with MySQL Community Edition 8.0.42)"`. Parse the community base version from each row.

   **Compare and emit:**
   - Source community version <= max(target community base) within the same major (e.g. source 8.0.42, target 3.10.4 = 8.0.42-base) → ✓. Record the matched Aurora version explicitly so the agent can use it in the create-cluster call.
   - Source > max(target community base) within the same major (e.g. source 8.0.45, latest available target = 8.0.42-base) → ⚠. Source is **ahead** of any available Aurora release by N patches. Aurora ships quarterly; community ships faster. Present **two** options to the user:
     1. Wait for the next Aurora release (typical cadence: quarterly). If the gap is >= 1 minor (e.g. source on a community version several quarters newer than any Aurora minor), this may be a multi-month wait.
     2. Proceed knowing the cluster will be at the older patch (e.g. 8.0.42); review the MySQL community release notes for `<latest-aurora-base>` → `<source>` to confirm the application doesn't depend on changes made in that range. The agent **MUST** show the relevant release-notes URL and require explicit user acknowledgment before proceeding.
   - **Do NOT offer "downgrade the RDS source" as a recovery option.** RDS MySQL does not support in-place minor-version downgrades. The only "downgrade" path is logical dump + restore to a new instance at the older version, which is functionally a separate migration. The agent **MUST NOT** suggest this — if the user explicitly asks for it, the agent **MUST** explain why it's not a viable recovery for a Path-2 (replication-based) migration and steer back to one of the two real options above.
   - Major version mismatch — source 5.7 with only Aurora MySQL 3 / 8.4 targets available → ✗ (upgrade RDS source first)
   - Source not in any community 5.7 / 8.0 / 8.4 line → ✗ (unsupported)

   The agent **MUST** emit the matched Aurora version explicitly in the assessment output so the user sees what they're getting before cluster creation runs. Do NOT use a hardcoded version range — Aurora's available minors change quarterly and vary by region.

2. **Storage engine inventory** — `SELECT TABLE_NAME, ENGINE FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '<db>' AND ENGINE <> 'InnoDB'`
   - empty result → ✓ (all InnoDB)
   - non-empty → ✗ (list the MyISAM/MEMORY tables; user must convert before migrating)

3. **Binary logging** — `SELECT @@log_bin, @@binlog_format;` and check `binlog retention hours` via `SELECT name, value FROM mysql.rds_configuration WHERE name = 'binlog retention hours'`
   - log_bin=1 AND retention >= 168h → ✓ (sufficient for Path 2 sync windows of any realistic size)
   - log_bin=1 AND retention >= 24h but < 168h → ⚠ (acceptable for small databases that sync in a few hours; raise to ≥168h before starting Path 2 on databases > ~50 GB or with bursty write loads)
   - log_bin=1 AND retention < 24h → ✗ (insufficient for any replication-based migration; raise via `CALL mysql.rds_set_configuration('binlog retention hours', 168);` first)
   - log_bin=0 → ✗ (enable automated backups first; binary logging is implicitly enabled when `BackupRetentionPeriod >= 1`)

4. **Parameter compatibility** — query the source's parameter group for parameters that don't have Aurora equivalents or that require translation:
   ```sql
   -- Example: parameters Aurora handles differently or doesn't expose
   SELECT @@innodb_file_per_table, @@lower_case_table_names,
          @@max_connections, @@character_set_server, @@collation_server;
   ```
   List each one as `<param>: <current> → <recommended for Aurora>` if a change is advised.

5. **Master credential mode** — `aws rds describe-db-instances --db-instance-identifier <id> --query 'DBInstances[0].MasterUserSecret'` (Path 2 only).
   - `MasterUserSecret` is `null` (fixed master password) → ✓ (read-replica creation will succeed with the source's existing credentials)
   - `MasterUserSecret` is set (managed credentials via Secrets Manager) → ⚠ — `aws rds create-db-cluster --replication-source-identifier ...` rejects sources with managed credentials. Two recovery paths, both require user authorization (Migration Safety Rule 4):
     - **Pre-stage a fixed password before starting Path 2** (recommended). Run `aws rds modify-db-instance --no-manage-master-user-password --master-user-password '<strong-pass>' --apply-immediately`. The instance enters `resetting-master-credentials` for ~30 seconds; **the application will get auth failures during this window** unless its connection config is updated first. Plan it as a deliberate, scheduled change, not a mid-migration scramble.
     - **Snapshot restore (Path 1) instead** — Path 1 does not require fixed credentials on the source. Choose this if the source must keep managed credentials.
   - **Do not** silently flip the source's credential mode mid-migration. Surface the choice and let the user pick.

**Recommendation logic:**
- If all checks pass and source is online with active writes → recommend Path 2 (read-replica promotion)
- If source is being decommissioned, or downtime tolerated → either path; default to Path 1 (snapshot restore) for simplicity
- If source has MyISAM tables → block until conversion done; recommend `ALTER TABLE ... ENGINE=InnoDB` for each
- If source has managed credentials and user wants Path 2 → present the two recovery paths above, default to the pre-stage option only with explicit authorization

**Estimating cutover downtime and sync time:**
- Cutover (Path 2): 10-60 seconds depending on application restart speed; typically < 30 seconds for an HTTP service that quiesces cleanly
- Replication sync time (Path 2): roughly 1 GB / minute on db.t3.medium-class instances under typical write load; faster on r6g and larger. Always state this as an estimate.

### Path 1: Snapshot Restore

**When to use:**
- Downtime is acceptable (minutes to hours depending on size)
- Source is small-to-medium (< 100 GB restores in reasonable time)
- You want the simplest possible path

**Steps:**
1. Take a manual snapshot of the RDS MySQL source:
   ```bash
   aws rds create-db-snapshot \
     --db-snapshot-identifier rds-to-aurora-migration \
     --db-instance-identifier <rds-instance-id>
   ```
2. Wait for the snapshot to reach `available`:
   ```bash
   aws rds wait db-snapshot-available \
     --db-snapshot-identifier rds-to-aurora-migration
   ```
3. Restore the snapshot as an Aurora MySQL cluster:
   ```bash
   aws rds restore-db-cluster-from-snapshot \
     --db-cluster-identifier my-aurora-cluster \
     --snapshot-identifier arn:aws:rds:<region>:<account>:snapshot:rds-to-aurora-migration \
     --engine aurora-mysql \
     --engine-version 8.0.mysql_aurora.3.07.1
   ```
   When the snapshot is a DB *instance* snapshot (taken from an RDS source, not from another Aurora cluster), pass the **full snapshot ARN**. RDS otherwise looks for a DB *cluster* snapshot by that name and fails with `DBClusterSnapshotNotFoundFault`.
4. Wait for the cluster to reach `available`. `restore-db-cluster-from-snapshot` is asynchronous; subsequent `modify-db-cluster` or `create-db-instance` calls fail with `InvalidDBClusterStateFault` while the cluster is still `creating`:
   ```bash
   aws rds wait db-cluster-available \
     --db-cluster-identifier my-aurora-cluster
   ```
5. Add a writer instance (required; the restore command only creates the cluster):
   - **Aurora MySQL 3 (db.serverless target):** first set the Serverless v2 scaling configuration on the cluster, then create the instance:
     ```bash
     aws rds modify-db-cluster \
       --db-cluster-identifier my-aurora-cluster \
       --serverless-v2-scaling-configuration MinCapacity=0.5,MaxCapacity=4 \
       --apply-immediately

     aws rds create-db-instance \
       --db-instance-identifier my-aurora-cluster-writer \
       --db-cluster-identifier my-aurora-cluster \
       --db-instance-class db.serverless \
       --engine aurora-mysql
     ```
     `db.serverless` is Aurora MySQL 3 only; without the scaling config first, `create-db-instance` fails with `Set the Serverless v2 scaling configuration on the parent DB cluster…`
   - **Aurora MySQL 2 (5.7-compatible target):** use a provisioned instance class. `db.serverless` is not supported on Aurora MySQL 2.
     ```bash
     aws rds create-db-instance \
       --db-instance-identifier my-aurora-cluster-writer \
       --db-cluster-identifier my-aurora-cluster \
       --db-instance-class db.t3.small \
       --engine aurora-mysql
     ```
6. Enable Data API (Aurora MySQL 3 only) — restore does **not** auto-enable Data API even though the MCP's `create_cluster` tool does. Without this step, `database_type: 'aurora-mysql'` + `rdsapi` cannot connect.
   ```bash
   aws rds modify-db-cluster \
     --db-cluster-identifier my-aurora-cluster \
     --enable-http-endpoint \
     --apply-immediately
   ```
7. Connect through the MCP with `database_type: 'aurora-mysql'` + `rdsapi` and verify row counts against the source.
8. Cut the application over by repointing to the Aurora writer endpoint.

**What gets copied:** data, indexes, stored procedures, triggers, views, user grants in `mysql.*` system tables.

**What does NOT get copied:**
- Parameter groups — Aurora requires Aurora-specific parameter groups; do not reuse the RDS parameter group
- Security groups — must be reattached
- Option groups — Aurora does not use option groups; verify features like `audit_log` map to Aurora equivalents
- CloudWatch log export settings — re-enable audit/error/general/slowquery on the Aurora side

**Cutover checklist:**
- [ ] Stop application writes to source RDS
- [ ] Take a final snapshot
- [ ] Restore as Aurora
- [ ] Verify row counts with the MCP: `SELECT TABLE_NAME, TABLE_ROWS FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '<db>'` on both sides
- [ ] Verify schema with `mcp_mysql_get_table_schema` on key tables
- [ ] Update app DB endpoint to Aurora writer endpoint
- [ ] Restart application
- [ ] Monitor errors for 30 minutes

**Rollback plan:** The original RDS cluster is untouched. To roll back, repoint the app back to the RDS endpoint and investigate.

### Path 2: Read-Replica Promotion (Recommended, Near-Zero Downtime)

**Migration Safety Rules (MUST follow)**

These rules are enforced for every Path 2 cutover the agent orchestrates. They take precedence over any speed/convenience consideration.

1. The source RDS instance **MUST remain fully operational and serving production traffic** during Aurora read replica creation and replication sync. The agent **MUST NOT** stop, modify, reboot, or redirect traffic from the source application until **ALL** of the following are true:
   - The Aurora read replica cluster reports `available`
   - The Aurora writer instance reports `available`
   - `AuroraBinlogReplicaLag` is observed at **0 seconds for two consecutive 1-minute CloudWatch samples** (a single 0 reading immediately after the writer comes up can be the metric not yet populated, not actual catch-up — wait for two)
   - The user has explicitly confirmed promotion can proceed
2. The agent **MUST emit a written cutover plan** before any traffic-affecting step. The plan MUST list every remaining action with timestamps and MUST label each action `traffic-affecting: yes` or `traffic-affecting: no`. The user MUST acknowledge the plan before execution. Suggested template:
   ```
   Cutover plan for <cluster-id>:
   T+0  [traffic-affecting: no]   Capture current source binlog position
   T+0  [traffic-affecting: no]   Verify AuroraBinlogReplicaLag = 0 (sample 1 of 2)
   T+1m [traffic-affecting: no]   Verify AuroraBinlogReplicaLag = 0 (sample 2 of 2)
   T+2m [traffic-affecting: yes]  Quiesce application writes to source
   T+2m [traffic-affecting: yes]  Invoke promote-read-replica-db-cluster
   T+3m [traffic-affecting: yes]  Repoint application to Aurora writer endpoint
   T+3m [traffic-affecting: no]   Run post-migration validation workflow
   ```
3. Application downtime is **ONLY** acceptable during the promotion step itself — from `promote-read-replica-db-cluster` invocation through application repointing. Total expected window: 10–60 seconds.
4. The agent **MUST NOT** modify the source RDS instance's master credentials, parameter group, or storage settings during migration unless the pre-migration assessment surfaced an incompatibility AND the user explicitly authorized the change. If the source uses managed master credentials and read-replica creation requires a fixed password, the agent MUST surface the requirement, present the impact (brief credential reset window), and obtain user confirmation before changing.

**When to use:**
- Minimize downtime (seconds, not minutes)
- Source is online and accepting writes during migration preparation
- Source and target are on the same major MySQL version

**How it works:** Aurora MySQL can be created as a read replica of an existing RDS MySQL instance using native MySQL binlog replication. The Aurora cluster stays in sync with the RDS source; when you are ready, you promote the replica and cut over the application.

**Steps:**
1. Ensure the RDS source has binlog enabled (`binlog_format=ROW`, `binlog_row_image=FULL`) and retains logs for long enough:
   ```sql
   CALL mysql.rds_set_configuration('binlog retention hours', 168);
   ```
2. Check whether the RDS source has encryption at rest enabled:
   ```bash
   aws rds describe-db-instances --db-instance-identifier <rds-instance-id> \
     --query 'DBInstances[0].[StorageEncrypted,KmsKeyId]' --output text
   ```
   If `StorageEncrypted` is `True`, the Aurora replica must use the same KMS key. RDS does not inherit encryption settings; without `--storage-encrypted --kms-key-id`, `create-db-cluster` fails with `Migrating an encrypted instance to an unencrypted cluster is not supported`.
3. Create the Aurora read replica:
   ```bash
   aws rds create-db-cluster \
     --db-cluster-identifier my-aurora-replica \
     --engine aurora-mysql \
     --replication-source-identifier arn:aws:rds:<region>:<account>:db:<rds-instance-id> \
     --storage-encrypted \
     --kms-key-id <source-kms-key-arn>
   ```
   Drop `--storage-encrypted` and `--kms-key-id` if the RDS source is unencrypted.
4. Wait for the replica cluster to reach `available`. `create-db-cluster` is asynchronous; the next `modify-db-cluster` or `create-db-instance` calls fail with `InvalidDBClusterStateFault` while the cluster is still `creating`:
   ```bash
   aws rds wait db-cluster-available \
     --db-cluster-identifier my-aurora-replica
   ```
5. Add a writer instance (required):
   - **Aurora MySQL 3 (db.serverless target):**
     ```bash
     aws rds modify-db-cluster \
       --db-cluster-identifier my-aurora-replica \
       --serverless-v2-scaling-configuration MinCapacity=0.5,MaxCapacity=4 \
       --apply-immediately

     aws rds create-db-instance \
       --db-instance-identifier my-aurora-replica-writer \
       --db-cluster-identifier my-aurora-replica \
       --db-instance-class db.serverless \
       --engine aurora-mysql
     ```
   - **Aurora MySQL 2 (5.7-compatible target):** use a provisioned class; `db.serverless` is Aurora MySQL 3 only.
     ```bash
     aws rds create-db-instance \
       --db-instance-identifier my-aurora-replica-writer \
       --db-cluster-identifier my-aurora-replica \
       --db-instance-class db.t3.small \
       --engine aurora-mysql
     ```
6. Wait for the replica to catch up. Monitor `AuroraBinlogReplicaLag` in CloudWatch — **target lag = 0 seconds for two consecutive 1-minute CloudWatch samples** before cutover. A single 0 reading immediately after the writer comes up can be the metric not yet populated, not actual catch-up. Alternately, connect via MCP with `database_type: 'aurora-mysql'` and run:
   ```sql
   SHOW REPLICA STATUS\G
   ```
   Look for `Seconds_Behind_Source: 0`.
7. **Emit the cutover plan and obtain explicit user confirmation before any traffic-affecting step.** See "Migration Safety Rules" above for the required plan template.
8. **(Traffic-affecting)** Stop writes to the RDS source briefly (the actual downtime window).
9. Verify zero lag on the Aurora side.
10. **(Traffic-affecting)** Promote the Aurora replica to a standalone cluster:
    ```bash
    aws rds promote-read-replica-db-cluster \
      --db-cluster-identifier my-aurora-replica
    ```
11. **(Traffic-affecting)** Update the application to point to the Aurora writer endpoint.
12. **(Traffic-affecting)** Restart the application.
13. Run the post-migration validation workflow and emit the structured `Migration validation: ✓/⚠/✗` block.

**Cutover checklist:**
- [ ] Binlog retention set on source
- [ ] Source encryption status checked; `--storage-encrypted` + `--kms-key-id` passed if source is encrypted
- [ ] Aurora replica created and writer instance added (Serverless v2 scaling config set first if `db.serverless`)
- [ ] Replica caught up: `AuroraBinlogReplicaLag = 0` for **two consecutive 1-minute samples**
- [ ] Cutover plan emitted; user explicitly confirmed promotion can proceed
- [ ] Application writes quiesced (traffic-affecting; downtime window starts here)
- [ ] Final lag check shows 0 seconds behind
- [ ] `promote-read-replica-db-cluster` invoked
- [ ] Promotion complete (cluster no longer shows a source)
- [ ] Application repointed to Aurora writer endpoint (downtime window ends here)
- [ ] Post-migration validation workflow run; `Migration validation: ✓/⚠/✗` block emitted
- [ ] Monitor for 30 minutes

**Downtime:** seconds (quiesce window + promotion API call latency).

**Rollback plan:** Before promotion, rollback is trivial — destroy the Aurora replica and point the app back at RDS. After promotion, the Aurora cluster is independent; rolling back means replicating the other direction (treat as a new migration).

### Post-Migration Validation Workflow

After cutover (snapshot restore or read-replica promotion), run a structured validation pass through the MCP and emit results in this format:

```
Migration validation:
✓ / ✗ Aurora cluster <cluster-id> created successfully
✓ / ✗ Writer endpoint: <endpoint>
✓ / ✗ Row count validation:
  - <table>: <n> rows (match | drift: source=<a> target=<b>)
  ...
✓ / ✗ Schema parity: <N> tables checked (<all match | diffs listed>)
✓ / ✗ Index parity: <N> indexes checked (<all match | diffs listed>)
Migration complete. Cutover downtime: <seconds> seconds.
```

**Steps:**

1. **Cluster health** — confirm the Aurora cluster reports `available` and the writer endpoint resolves:
   ```bash
   aws rds describe-db-clusters --db-cluster-identifier <cluster> \
     --query 'DBClusters[0].[Status,Endpoint]' --output text
   ```

2. **Row-count parity** — run on **both** the source (via `mysqlwire` + `mysql`) and the target (via `rdsapi` + `aurora-mysql`), then diff:
   ```sql
   SELECT TABLE_NAME, TABLE_ROWS
   FROM INFORMATION_SCHEMA.TABLES
   WHERE TABLE_SCHEMA = '<your-database>'
   ORDER BY TABLE_NAME;
   ```
   Note: `TABLE_ROWS` for InnoDB is an estimate. For exact counts on critical tables, use `SELECT COUNT(*) FROM <table>` per table.

3. **Schema parity** — call `mcp_mysql_get_table_schema` on each critical table on both sides and compare the column lists, types, and indexes.

4. **Index parity** — list indexes on both sides:
   ```sql
   SELECT TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX, COLUMN_NAME
   FROM INFORMATION_SCHEMA.STATISTICS
   WHERE TABLE_SCHEMA = '<your-database>'
   ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;
   ```
   Aurora MySQL preserves indexes on snapshot restore and read-replica creation; mismatches usually indicate a schema change made between assessment and cutover.

5. **Cutover downtime measurement** — when the agent orchestrates Path 2, capture timestamps at quiesce-start and after the application reconnects to the Aurora endpoint, then report the delta as the cutover window.

**What to do on drift:**
- Drift on `TABLE_ROWS` of < 1% on InnoDB tables is normal (estimate variance) — confirm with `COUNT(*)`
- Real row-count drift means binlog replication didn't fully catch up before promotion. Once `promote-read-replica-db-cluster` completes, the Aurora cluster is independent and cannot be re-promoted. Investigate the missing transactions (compare the source binlog position at quiesce with the last position applied on Aurora before promotion) and replay them manually on the Aurora cluster, or fall back to the rollback plan from Path 2 (replicate in the other direction; treat as a new migration).
- Schema or index drift on a fresh restore should be zero. Drift here is a steering bug; surface it to the user rather than silently proceeding.

## Replication: Read Replicas, Global Database, Binlog

Aurora MySQL supports three replication surfaces: in-region Aurora replicas (same cluster), cross-region via Aurora Global Database, and binlog output to external consumers.

### In-Region Aurora Read Replicas

**When to use:** offload read-heavy workloads (reporting, analytics, full-text search) from the writer. Replicas share storage with the writer (copy-on-write semantics), so lag is typically < 20 ms.

**Configuration:**
- Up to 15 replica instances per Aurora MySQL cluster
- Reader endpoint load-balances across all replicas
- Each replica is promotable to writer (automatic failover when enabled)
- For Serverless v2 clusters, replicas are also Serverless v2 and scale independently

**Choosing a reader instance class:**

The right size depends on the workload, not a one-size-fits-all answer. Apply this rubric:

| Workload signal | Recommended reader class |
|------------------|--------------------------|
| Source cluster is Serverless v2; reporting load is variable / unpredictable; dev/test or low-volume production | `db.serverless` (Aurora MySQL 3 only) — scales 0.5-128 ACU on demand |
| Very small cluster (< 50 GB, < 100 reads/sec); cost-sensitive | `db.t3.medium` or `db.t4g.medium` (provisioned, burstable; budget option) |
| Analytics-heavy reads on million-row+ datasets, sustained large buffer pool needed for sequential scans, Graviton-friendly | `db.r6g.large` or `db.r7g.large` (memory-optimized) |
| Sustained CPU pressure or buffer-pool eviction observed on a smaller class | scale up to `db.r6g.xlarge` or larger based on CloudWatch CPU and BufferCacheHitRatio |
| Same major version requirement: Aurora MySQL 2 | provisioned class only — `db.serverless` is not supported on Aurora 2 |

Default to `db.serverless` for Aurora MySQL 3 unless the user describes one of the workload signals above. Always state the reasoning when picking a class so the user can override.

**Add a replica (Aurora MySQL 3 with Serverless v2 default):**

Aurora MySQL 3 clusters using `db.serverless` need a Serverless v2 scaling configuration before adding the instance. The MCP's `create_cluster` tool does this automatically; if you created the cluster manually, set it first:
```bash
aws rds modify-db-cluster \
  --db-cluster-identifier my-aurora-cluster \
  --serverless-v2-scaling-configuration MinCapacity=0.5,MaxCapacity=4 \
  --apply-immediately
```

Then add the reader:
```bash
aws rds create-db-instance \
  --db-instance-identifier my-aurora-reader-1 \
  --db-cluster-identifier my-aurora-cluster \
  --db-instance-class db.serverless \
  --engine aurora-mysql
```

Substitute `db.serverless` with the class chosen by the rubric above. For Aurora MySQL 2, always use a provisioned class.

**Tuning a reader for analytical workloads (optional):**

Default Aurora parameter groups are reasonable for most workloads. Only create a custom reader parameter group when measurements show specific issues. The four parameters most often adjusted for analytics workloads:

| Parameter | Default | When to raise | Trade-off |
|-----------|---------|---------------|-----------|
| `long_query_time` | 10 s | Raise to 30 s if dashboard queries are legitimately slow (>10 s) and flooding the slow query log with non-actionable entries | Slower queries no longer captured; verify dashboards are < new threshold |
| `max_execution_time` | 0 (unlimited) | Set to e.g. 300000 ms (5 min) to bound runaway dashboard queries while still allowing complex aggregations | A query that legitimately needs > limit will fail; size based on real workload |
| `tmp_table_size` | 16 MB | Raise to e.g. 256 MB if `Created_tmp_disk_tables` is high (in-memory temp tables spilling to disk) | Costs RAM proportional to value × concurrent threads |
| `innodb_buffer_pool_size` | 75% of instance memory (Aurora-managed) | Aurora manages this automatically; do **not** override unless instructed by AWS support | Wrong values harm performance |

Workflow when the user asks to "tune the reader for analytics":
1. Measure first via Performance Insights / `SHOW GLOBAL STATUS` (look at `Slow_queries`, `Created_tmp_disk_tables`, `Innodb_buffer_pool_reads`)
2. Create a custom DB **instance** parameter group for the reader. Each instance in a cluster can have its own instance parameter group, so this scopes the tuning to the reader without affecting the writer. Do **not** use `create-db-cluster-parameter-group` — that applies to every instance in the cluster including the writer.
3. Apply only the parameters that the measurements justify; leave the rest at defaults
4. Reboot the reader instance for static parameters to take effect; document which were changed and why

```bash
# Create a custom DB INSTANCE parameter group for the reader (Aurora MySQL 3 / 8.0).
# This scopes tuning to the reader instance only — the writer keeps its own parameter group.
aws rds create-db-parameter-group \
  --db-parameter-group-name reader-analytics \
  --db-parameter-group-family aurora-mysql8.0 \
  --description "Reader-only tuning for analytical workloads"

aws rds modify-db-parameter-group \
  --db-parameter-group-name reader-analytics \
  --parameters \
    'ParameterName=long_query_time,ParameterValue=30,ApplyMethod=immediate' \
    'ParameterName=max_execution_time,ParameterValue=300000,ApplyMethod=immediate' \
    'ParameterName=tmp_table_size,ParameterValue=268435456,ApplyMethod=pending-reboot'

aws rds modify-db-instance \
  --db-instance-identifier my-aurora-reader-1 \
  --db-parameter-group-name reader-analytics \
  --apply-immediately

aws rds reboot-db-instance --db-instance-identifier my-aurora-reader-1
```

**Route reads to the reader endpoint:**
- Writer endpoint: `<cluster-id>.cluster-<id>.<region>.rds.amazonaws.com` — writes and reads that must see the latest write
- Reader endpoint: `<cluster-id>.cluster-ro-<id>.<region>.rds.amazonaws.com` — read-only; DNS-round-robins across replicas

**Application patterns:**
- Dual-pool: one writer pool on writer endpoint, one reader pool on reader endpoint
- Route analytical or eventually-consistent reads (dashboards, historical reports) to reader
- Route read-your-write reads to writer

**Monitoring:**
- `AuroraReplicaLag` — milliseconds between writer apply and replica apply; alarm > 100 ms sustained
- `AuroraReplicaLagMaximum` and `AuroraReplicaLagMinimum` — variance across replicas
- `DatabaseConnections` — per-instance; imbalance across replicas suggests DNS caching or pool misconfig

### Aurora Global Database (Cross-Region)

**When to use:** low-latency reads in a second region, regional disaster recovery, managed planned failover.

**How it works:** one primary region with a full Aurora cluster; one or more secondary regions with read-only replicas. Replication is performed at the storage layer, not SQL, so lag is typically < 1 second even across continents.

**Setup:**
1. Ensure the source Aurora cluster does **not** use RDS-managed credentials. `create-global-cluster` rejects clusters with `MasterUserPassword` managed by RDS (`Can't create an Aurora global database. MasterUserPassword for the specified source DB cluster is managed by RDS`). Disable managed credentials first if needed:
   ```bash
   aws rds modify-db-cluster \
     --db-cluster-identifier my-aurora-cluster \
     --no-manage-master-user-password \
     --master-user-password '<set-a-password>' \
     --apply-immediately
   ```
   Note: clusters created via the MCP's `create_cluster` tool use managed credentials by default.
2. Create the Global Database with an existing Aurora MySQL cluster as primary:
   ```bash
   aws rds create-global-cluster \
     --global-cluster-identifier my-global-db \
     --source-db-cluster-identifier arn:aws:rds:us-west-2:<account>:cluster:my-aurora-cluster
   ```
3. Add a secondary region cluster:
   ```bash
   aws rds create-db-cluster \
     --db-cluster-identifier my-aurora-eu \
     --engine aurora-mysql \
     --global-cluster-identifier my-global-db \
     --region eu-west-1
   ```
4. Wait for the secondary cluster to reach `available`. `create-db-cluster` is asynchronous; the next `modify-db-cluster` fails with `InvalidDBClusterStateFault` while the cluster is still `creating`:
   ```bash
   aws rds wait db-cluster-available \
     --db-cluster-identifier my-aurora-eu \
     --region eu-west-1
   ```
5. Set Serverless v2 scaling config on the secondary cluster (if using `db.serverless`):
   ```bash
   aws rds modify-db-cluster \
     --db-cluster-identifier my-aurora-eu \
     --serverless-v2-scaling-configuration MinCapacity=0.5,MaxCapacity=4 \
     --apply-immediately \
     --region eu-west-1
   ```
6. Add at least one reader instance in the secondary region:
   ```bash
   aws rds create-db-instance \
     --db-instance-identifier my-aurora-eu-reader-1 \
     --db-cluster-identifier my-aurora-eu \
     --db-instance-class db.serverless \
     --engine aurora-mysql \
     --region eu-west-1
   ```

**Reads:** connect to the secondary cluster's reader endpoint for low-latency reads in that region.

**Writes:** always go to the primary region. Applications in the secondary region write across a cross-region link (adds latency), or queue writes and let the primary region process them.

**Monitoring:**
- `AuroraGlobalDBReplicationLag` — milliseconds between primary writer commit and secondary apply; alarm > 1000 ms sustained
- `AuroraGlobalDBRPOLag` — recovery point objective lag; how much data would be lost in an unplanned failover

**Planned failover:** fail the global database over to a secondary region in seconds via `failover-global-cluster` (requires prior configuration of a managed RPO target). Use for region-evacuation exercises or DR drills.

**Unplanned failover (detach and promote):** if the primary region is unreachable, detach the secondary and promote it. This is a hard operation and the old primary cannot be reattached without rebuilding.

### Binlog Replication to External Consumers

**When to use:** stream row-level changes from Aurora MySQL into Kafka, Kinesis, OpenSearch, Debezium, or another MySQL instance outside AWS.

**Enable binlog on the Aurora cluster:**
1. Set the following cluster parameters (DB cluster parameter group):
   - `binlog_format = ROW`
   - `binlog_row_image = FULL`
   - `binlog_checksum = NONE` (required for some CDC consumers)
2. Reboot the writer instance for the parameter changes to apply.

**Set binlog retention:**
```sql
CALL mysql.rds_set_configuration('binlog retention hours', 168);
```
Retention must cover at least the maximum outage window of downstream consumers.

**Create a replication user with the right grants:**
```sql
CREATE USER 'repl_user'@'%' IDENTIFIED BY '<strong-password>';
GRANT REPLICATION REPLICA, REPLICATION CLIENT ON *.* TO 'repl_user'@'%';
```

**Point an external consumer at the cluster:** the consumer uses the MySQL wire protocol with `CHANGE REPLICATION SOURCE TO` (or its client-library equivalent):
```sql
CHANGE REPLICATION SOURCE TO
  SOURCE_HOST='<aurora-writer-endpoint>',
  SOURCE_USER='repl_user',
  SOURCE_PASSWORD='<password>',
  SOURCE_AUTO_POSITION=1;
START REPLICA;
```
This is standard MySQL 8.0 replication syntax; the same pattern works for any downstream consumer that speaks the MySQL replication protocol, including open-source CDC tools (e.g. Debezium), managed AWS pipelines (e.g. Amazon OpenSearch Ingestion), and external MySQL instances. Consumer configuration is outside the scope of this guide — refer to the consumer's own documentation.

**Monitoring:**
- `AuroraBinlogReplicaLag` — CloudWatch metric for outbound binlog lag from the Aurora writer
- `SHOW REPLICA STATUS\G` on the consumer side — `Seconds_Behind_Source`, `Replica_IO_Running`, `Replica_SQL_Running`, `Last_Error`

### Replication Lag Monitoring Quick Reference

| Metric | Where | What it measures | Target |
|--------|-------|------------------|--------|
| `AuroraReplicaLag` | CloudWatch, per reader instance | In-region replica apply lag (storage-level) | < 100 ms |
| `AuroraGlobalDBReplicationLag` | CloudWatch, per secondary region cluster | Cross-region replica apply lag (storage-level) | < 1000 ms |
| `AuroraGlobalDBRPOLag` | CloudWatch, per secondary region cluster | Recovery point objective lag | Per RPO target |
| `AuroraBinlogReplicaLag` | CloudWatch, on writer | Binlog emission lag to external consumers | < 5 s |
| `Seconds_Behind_Source` | `SHOW REPLICA STATUS\G` on consumer | Consumer-side apply lag | Consumer-specific |

**Recommended CloudWatch alarms:**
- `AuroraReplicaLag > 100ms for 5 minutes` — in-region replica falling behind; investigate
- `AuroraGlobalDBReplicationLag > 5000ms for 5 minutes` — cross-region degradation; may indicate network issue
- `AuroraBinlogReplicaLag > 30s for 5 minutes` — downstream pipeline stalled; check consumer

## Cost Optimization

**Provisioned:**
- Right-size based on usage
- Reserved Instances for predictable workloads
- Aurora I/O-Optimized for high I/O

**Serverless v2:**
- Set appropriate min ACU (avoid over-provisioning)
- Monitor ACUUtilization to optimize max ACU
- Use RDS Proxy to reduce connection overhead
- Consider I/O-Optimized if I/O costs high

**General:**
- Drop unused indexes
- Archive old data
- Optimize slow queries
- Appropriate backup retention
