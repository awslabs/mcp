# Aurora PostgreSQL Development Guide

Best practices for Aurora PostgreSQL development using MCP server. Covers provisioned instances and Aurora Serverless v2.

## Aurora Serverless v2

**Characteristics:**
- Auto-scales 0.5-128 ACU in seconds (1 ACU ≈ 2 GB RAM ≈ db.t3.medium)
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
2. Run `EXPLAIN (ANALYZE, BUFFERS)` to identify seq scans
3. Check Performance Insights
4. Update statistics: `VACUUM ANALYZE table_name`

**Connection Failures:**
1. Check connection pool config (sizes, timeouts)
2. Verify DNS TTL < 30s
3. Check CloudWatch DatabaseConnections
4. For Serverless v2: verify capacity and RDS Proxy

**Storage Growth:**
1. Query unused indexes (pg_stat_user_indexes)
2. Check bloat (pg_stat_user_tables)
3. Run VACUUM or REINDEX

**Schema Migrations:**
1. Check if ALTER requires table rebuild
2. Use CONCURRENTLY, shadow columns, or NOT VALID patterns
3. Estimate time: ~1-2 min/GB
4. Test on dev cluster first

## Cluster Setup

**Initial Config:**
- Create via MCP tool start_create_cluster_job
- MCP tool Start_create_cluster_job return immediately with job id
- Create script to call MCP tool get_job_status with jod id to check cluster creation status
- Create Postgres database via MCP tool run_query
- Store credentials in Secrets Manager
- Enable Performance Insights and Enhanced Monitoring

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
- Normalize to 3NF; denormalize only when proven necessary
- Use precise types: INT over BIGINT, VARCHAR(50) over VARCHAR(255)
- Apply NOT NULL where required
- Use CHECK for limited value sets
- Include deleted_at for soft deletes
- Use TIMESTAMPTZ for timestamps

**Keys:**
- Primary: SERIAL/BIGSERIAL (default), UUID only when needed
- Foreign: Always define FKs, choose ON DELETE behavior, index all FK columns

## Index Strategy

**Always Index:**
- Primary keys (automatic)
- Foreign keys (not auto-indexed in PostgreSQL)
- WHERE, ORDER BY, GROUP BY, JOIN columns

**Index Patterns:**
- Composite: order by selectivity (most selective first)
- Covering: use INCLUDE for SELECT columns
- Partial: for common filters (WHERE status = 'active')
- Expression: for computed columns

**Never Index:**
- Low-cardinality columns (unless in composite)
- Every column (write overhead)
- Redundant indexes (a,b covers a)
- Small tables (< 1000 rows)

**Analysis:**
- `EXPLAIN (ANALYZE, BUFFERS)` for seq scans
- pg_stat_statements for slow queries
- pg_stat_user_indexes for usage

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
- Batch INSERTs
- Use INSERT ... ON CONFLICT for upserts
- Wrap multi-statement ops in transactions
- Avoid long transactions (blocks autovacuum)
- Use RETURNING for inserted/updated data

**Optimization Process:**
1. Find slow queries (Performance Insights)
2. Run `EXPLAIN (ANALYZE, BUFFERS)`
3. Look for: Seq Scan, high shared reads, rows removed by filter
4. Fix: add indexes, rewrite query, or restructure schema
5. Validate with re-run

## Development Workflow

**Standard Cycle:**
1. Create cluster via MCP
2. Create database: `CREATE DATABASE mydb;`
3. Design schema
4. Create tables and indexes (use CONCURRENTLY)
5. Develop queries
6. Analyze with `EXPLAIN (ANALYZE, BUFFERS)`
7. Optimize and iterate

**Migrations:**
- Version control all DDL
- Test on dev cluster first
- Maintain rollback scripts
- Use migration tools (Flyway/Liquibase/Alembic)

## Safe Schema Changes

**High-Risk (Table Rebuild):**
- Adding NOT NULL without default (pre-PG 11)
- Changing column types
- Modifying primary keys
- Rebuilding indexes without CONCURRENTLY

**Low-Risk (Fast/Instant):**
- Adding nullable columns
- Adding columns with defaults (PG 11+)
- Changing defaults (metadata only)
- Renaming tables/columns (metadata only)
- CONCURRENTLY index operations
- Dropping columns (PG 11+, metadata only)

**Non-Blocking Patterns:**

```sql
-- Add nullable column (safe, instant)
ALTER TABLE users ADD COLUMN last_login TIMESTAMPTZ;

-- Add column with default (PostgreSQL 11+, instant)
ALTER TABLE users ADD COLUMN status VARCHAR(20) DEFAULT 'active';

-- Change default value (safe, metadata only)
ALTER TABLE users ALTER COLUMN status SET DEFAULT 'inactive';

-- Add check constraint (NOT VALID first, then validate)
ALTER TABLE users
ADD CONSTRAINT check_age CHECK (age >= 18) NOT VALID;

-- Validate separately (can be done during low traffic)
ALTER TABLE users VALIDATE CONSTRAINT check_age;
```

**Concurrent Index Creation:**

```sql
-- Create index without blocking writes
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);

-- Drop index without blocking
DROP INDEX CONCURRENTLY idx_users_old;

-- Monitor progress
SELECT
  phase,
  round(100.0 * blocks_done / nullif(blocks_total, 0), 1) AS "% complete",
  active_workers
FROM pg_stat_progress_create_index;
```

## Safe ALTER Patterns

**Adding NOT NULL Column:**
```sql
-- Multi-step approach
ALTER TABLE users ADD COLUMN phone VARCHAR(20);
UPDATE users SET phone = '' WHERE phone IS NULL AND id BETWEEN 1 AND 10000;
-- Repeat in batches
ALTER TABLE users ALTER COLUMN phone SET NOT NULL;
```

**Changing Column Type:**
```sql
-- Shadow column approach
ALTER TABLE orders ADD COLUMN amount_new DECIMAL(12,2);
UPDATE orders SET amount_new = amount WHERE amount_new IS NULL LIMIT 10000;
-- Repeat, deploy dual-write code, verify, then swap
BEGIN;
ALTER TABLE orders DROP COLUMN amount;
ALTER TABLE orders RENAME COLUMN amount_new TO amount;
COMMIT;
```

**Adding Foreign Key:**
```sql
-- NOT VALID then validate
ALTER TABLE orders
ADD CONSTRAINT fk_customer
FOREIGN KEY (customer_id) REFERENCES customers(id) NOT VALID;

ALTER TABLE orders VALIDATE CONSTRAINT fk_customer;
```

**Dropping Column:**
```sql
-- Stop writes first, wait, then drop
ALTER TABLE users DROP COLUMN deprecated_field;
-- PG 11+: instant (metadata only)
```

## Migration Workflow

**Pre-Migration:**
```sql
-- Check size and row count
SELECT schemaname, tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
  n_live_tup AS rows
FROM pg_stat_user_tables WHERE tablename = 'users';

-- Check long-running queries
SELECT pid, usename, state, query_start, query
FROM pg_stat_activity
WHERE state != 'idle' AND query_start < NOW() - INTERVAL '5 minutes';
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
\d users  -- Verify schema
VACUUM ANALYZE users;  -- Update statistics
```

## Zero-Downtime Tools

**Blue/Green Deployments:**
- Create via MCP, apply changes to green, test, switch (< 1 min downtime)

**pg_repack:**
```bash
pg_repack -h cluster.amazonaws.com -U user -d db -t users
```

**pgBouncer:**
- Connection pooling with PAUSE/RESUME for maintenance

## Schema Change Quick Reference

- **Add nullable column**: Direct ADD COLUMN (instant)
- **Add NOT NULL**: Add with DEFAULT (PG 11+) or add NULL → backfill → SET NOT NULL
- **Change type**: Shadow column (add → backfill → swap → drop)
- **Add index**: `CREATE INDEX CONCURRENTLY`
- **Drop index**: `DROP INDEX CONCURRENTLY`
- **Add FK**: Add NOT VALID → VALIDATE separately
- **Drop column**: Direct drop (PG 11+, instant metadata)
- **Rename**: `ALTER TABLE ... RENAME` (instant metadata)
- **Add CHECK**: Add NOT VALID → VALIDATE separately

## Finding Missing Indexes

**Using pg_stat_statements (requires extension):**
```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

SELECT substring(query, 1, 100) AS query,
    calls, total_exec_time / 1000 AS total_sec,
    mean_exec_time / 1000 AS mean_sec
FROM pg_stat_statements
WHERE calls > 100
ORDER BY mean_exec_time DESC LIMIT 20;
```

**Sequential scans (no extension):**
```sql
SELECT schemaname, tablename, seq_scan, seq_tup_read, idx_scan,
    seq_tup_read / NULLIF(seq_scan, 0) AS avg_seq_tup,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_stat_user_tables
WHERE seq_scan > 0
ORDER BY seq_tup_read DESC LIMIT 20;
```

## Unused Indexes

**Zero scans:**
```sql
SELECT schemaname, tablename, indexname, idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0 AND indexrelname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(indexrelid) DESC;
```

**Duplicate indexes:**
```sql
SELECT pg_size_pretty(SUM(pg_relation_size(idx))::BIGINT) AS size,
    (array_agg(idx))[1] AS idx1, (array_agg(idx))[2] AS idx2
FROM (
    SELECT indexrelid::regclass AS idx,
        (indrelid::text ||E'\n'|| indclass::text ||E'\n'|| indkey::text ||E'\n'||
         COALESCE(indexprs::text,'')||E'\n' || COALESCE(indpred::text,'')) AS key
    FROM pg_index
) sub
GROUP BY key HAVING COUNT(*) > 1
ORDER BY SUM(pg_relation_size(idx)) DESC;
```

## Bloat Detection

**Table bloat (no extension, fast):**
```sql
SELECT schemaname, relname AS tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||relname)) AS size,
    n_dead_tup, n_live_tup,
    round(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_pct
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC LIMIT 20;
-- If dead_pct > 20%: VACUUM
```

**Index bloat (requires pgstattuple):**
```sql
CREATE EXTENSION IF NOT EXISTS pgstattuple;

SELECT schemaname, tablename, indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size,
    round(100 * (1 - pgstatindex.avg_leaf_density)) AS bloat_pct
FROM pg_stat_user_indexes,
LATERAL pgstatindex(indexrelid) AS pgstatindex
WHERE pg_relation_size(indexrelid) > 1024*1024*10
ORDER BY (1 - pgstatindex.avg_leaf_density) DESC LIMIT 10;
-- If bloat_pct > 30%: REINDEX CONCURRENTLY
```

## Autovacuum Monitoring

**Vacuum status:**
```sql
SELECT schemaname, relname, last_vacuum, last_autovacuum, n_dead_tup,
    round(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_pct
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC LIMIT 20;
```

**Progress (running):**
```sql
SELECT pid, datname, relid::regclass AS table_name, phase,
    round(100.0 * heap_blks_scanned / NULLIF(heap_blks_total, 0), 2) AS scan_pct
FROM pg_stat_progress_vacuum;
```

**Tune for high-churn:**
```sql
ALTER TABLE high_churn_table SET (
    autovacuum_vacuum_scale_factor = 0.05,
    autovacuum_analyze_scale_factor = 0.05
);
```

## Query Optimization

**EXPLAIN ANALYZE:**
```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT ... FROM ... WHERE ...;
```

Look for:
- Seq Scan on large tables (need Index Scan)
- High "Buffers: shared read" (I/O bottleneck)
- "rows removed by filter" (inefficient filtering)
- Nested Loop on large datasets (consider Hash Join)

## Statistics Maintenance

```sql
VACUUM ANALYZE orders;  -- Specific table (recommended)
ANALYZE;  -- Entire database
VACUUM orders;  -- Reclaim space
VACUUM FULL orders;  -- Exclusive lock, use sparingly
```

## Connection Management

**RDS Proxy (Production):**
- Auto pooling, failover, IAM auth, Secrets Manager
- Critical for: Lambda, microservices, Serverless v2

**Pooling:**
- App-side: pgBouncer, HikariCP, ORM pools
- Configure min/max, idle timeouts
- Monitor via Performance Insights

**Best Practices:**
- Writer endpoint: writes only
- Reader endpoint: reads (load balanced)
- DNS TTL < 30s
- Test failover before production
- Serverless v2: Always use RDS Proxy or pooling

**Code Generation:**
When generating DB code, always include:
- Connection pooling (min/max)
- Retry logic with exponential backoff
- Connection timeouts
- Health checks
- Graceful error handling

Frameworks: Django, Flask, SQLAlchemy, FastAPI, Rails, Prisma, Drizzle, TypeORM, Sequelize, Spring Boot, Hibernate

**Seed Scripts:**
Make idempotent:
- Use `INSERT ... ON CONFLICT DO NOTHING`
- Check existence before creating
- Wrap in transactions

## Monitoring

**Performance Insights:**
- Tracks AAS, top SQL, wait events
- Free: 7 days, Paid: up to 2 years

**Slow Query Logging:**
```sql
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- 1 second
SELECT pg_reload_conf();
```

**CloudWatch Alerts:**
- CPUUtilization > 80%
- DatabaseConnections approaching max
- FreeableMemory low
- ReadLatency/WriteLatency spikes
- BufferCacheHitRatio < 95%
- Serverless v2: ServerlessDatabaseCapacity, ACUUtilization

**MCP Queries:**
- Table sizes: pg_total_relation_size
- Index usage: pg_stat_user_indexes
- Replication lag: pg_stat_replication
- Connections: pg_stat_activity

## Connection Examples

**Python (Psycopg3):**
```python
import psycopg
conn = psycopg.connect(
    host="cluster.amazonaws.com", port=5432, dbname="mydb",
    user="myuser", password="mypassword", sslmode="require"
)
```

**Python with Pool:**
```python
from psycopg_pool import ConnectionPool
pool = ConnectionPool(
    conninfo="host=cluster.amazonaws.com port=5432 dbname=mydb user=myuser password=mypassword sslmode=require",
    min_size=5, max_size=20, timeout=30
)
```

**Python with AWS Wrapper (failover):**
```python
from aws_advanced_python_wrapper import AwsWrapperConnection
import psycopg
conn = AwsWrapperConnection.connect(
    psycopg.Connection.connect, host="cluster.amazonaws.com",
    plugins="failover,host_monitoring", wrapper_dialect="aurora-pg"
)
```

**Python with IAM Auth:**
```python
import boto3
client = boto3.client('rds')
token = client.generate_db_auth_token(
    DBHostname=ENDPOINT, Port=5432, DBUsername=USER, Region=REGION
)
conn = psycopg.connect(host=ENDPOINT, user=USER, password=token, sslmode='verify-full')
```

**Node.js (pg):**
```javascript
const { Client } = require('pg');
const client = new Client({
  host: 'cluster.amazonaws.com', port: 5432, database: 'mydb',
  user: 'myuser', password: 'mypassword', ssl: { rejectUnauthorized: true }
});
```

**Node.js with Pool:**
```javascript
const { Pool } = require('pg');
const pool = new Pool({
  host: 'cluster.amazonaws.com', min: 5, max: 20,
  idleTimeoutMillis: 30000, connectionTimeoutMillis: 2000
});
```

**RDS Proxy:** Use proxy endpoint instead of cluster endpoint for auto pooling and failover.

**Connection Checklist:**
1. SSL/TLS: `sslmode='require'` or `sslmode='verify-full'`
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
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ
);

-- Composite index for common pattern
CREATE INDEX idx_users_status_created ON users(status, created_at DESC)
WHERE deleted_at IS NULL;

-- Partial index
CREATE INDEX idx_users_active ON users(email)
WHERE status = 'active' AND deleted_at IS NULL;
```

**Query Optimization:**
```sql
-- Before: SELECT * FROM orders WHERE customer_id = 123 ORDER BY created_at DESC;

-- Add index
CREATE INDEX CONCURRENTLY idx_orders_customer_created
ON orders(customer_id, created_at DESC);

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

## Pre-Production Checklist

**Schema:**
- Data model documented
- Access patterns identified
- Appropriate data types
- Primary keys on all tables
- Foreign keys indexed
- Indexes support queries
- EXPLAIN plans reviewed

**Infrastructure:**
- Backup retention: 7-35 days
- Multi-AZ enabled
- Encryption at rest (KMS)
- DNS TTL < 30s
- Connection pooling (RDS Proxy)
- Failover tested
- Serverless v2: min/max ACU configured

**Monitoring:**
- Performance Insights enabled
- CloudWatch alarms configured
- Slow query logging enabled
- Enhanced Monitoring enabled

## Index Management

**Before Adding:**
- Query is slow (Performance Insights)
- EXPLAIN shows seq scans or high buffer reads
- No similar indexes exist
- Tested on dev cluster
- Use CONCURRENTLY

**Before Dropping:**
- Zero usage 30+ days (pg_stat_user_indexes)
- Not enforcing uniqueness
- No app dependencies
- Tested on dev cluster
- Save CREATE statement for rollback

## Operational Triggers

**Performance Issues:**
- Check Performance Insights
- Run EXPLAIN (ANALYZE, BUFFERS)
- Add indexes for bottlenecks
- Check bloat, run VACUUM
- Serverless v2: check capacity constraints

**New Features:**
- Analyze query patterns
- Add indexes proactively
- Test with production-like data
- Monitor after deployment

**Storage Growth:**
- Query pg_stat_user_indexes
- Drop unused indexes
- Check bloat, run VACUUM/REINDEX
- Identify archival candidates

**Query Regression:**
- VACUUM ANALYZE
- Verify indexes via EXPLAIN
- Check bloat
- Adjust autovacuum settings

**Connection Issues:**
- Check DatabaseConnections metric
- Verify pool config
- Serverless v2: check scaling constraints
- Consider RDS Proxy

**Major Releases:**
- Test backup restore
- Update schema
- Review pool settings
- Test failover

## MCP Analysis Workflows

**Performance Issues:**
- Run missing index queries via MCP
- Check Performance Insights
- EXPLAIN problematic queries
- Add indexes for bottlenecks

**New Features:**
- Analyze query patterns
- Add indexes proactively
- Test with production data volumes

**Storage Growth:**
- Query pg_stat_user_indexes via MCP
- Drop unused indexes
- Check bloat, run VACUUM/REINDEX

**Query Regression:**
- Check stale statistics
- VACUUM ANALYZE affected tables
- Verify index usage
- Adjust autovacuum settings

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
