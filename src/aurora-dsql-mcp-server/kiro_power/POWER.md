---
name: "amazon-aurora-dsql"
displayName: "Build applications with Aurora DSQL"
description: "Build applications using a serverless, PostgreSQL-compatible database with scale-to-zero and pay-per-use pricing - built for applications at any scale."
keywords: ["aurora", "dsql", "postgresql", "serverless", "database", "sql", "aws", "distributed"]
author: "AWS"
---

# Amazon Aurora DSQL Power

## Overview

The Amazon Aurora DSQL Power provides access to Aurora DSQL, a serverless, PostgreSQL-compatible distributed SQL database with specific constraints and capabilities. Execute queries, manage schemas, handle migrations, and work with multi-tenant data while respecting DSQL's unique limitations.

Aurora DSQL is a true serverless database with scale-to-zero capability, zero operations overhead, and consumption-based pricing. It uses the PostgreSQL wire protocol but has specific limitations around foreign keys, array types, JSON columns, and transaction sizes.

**Key capabilities:**
- **Direct Query Execution**: Run SQL queries directly against your DSQL cluster via MCP tools
- **Schema Management**: Create tables, indexes, and manage DDL operations
- **Migration Support**: Execute schema migrations safely with proper transaction handling
- **Multi-Tenant Patterns**: Built-in tenant isolation and data scoping
- **IAM Authentication**: Automatic token generation using AWS credentials

---

## Available Steering Files

This power includes the following steering files in [steering](./steering)
- **development-guide**
  - ALWAYS load before implementing schema changes or database operations
  - MAY load when planning database application design
  - DSQL Guidelines and Operational Rules
- **language**
  - MUST load when making language-specific implementation choices
  - Driver selection, framework patterns, connection code for various languages
- **dsql-examples**
  - CAN Load when looking for specific implementation examples
  - Specific examples and implementation patterns
- **troubleshooting**
  - SHOULD Load when debugging errors or unexpected behavior
  - Common pitfalls and errors and how to solve
- **mcp-setup**
  - ALWAYS load for MCP server configurations or MCP server operations
  - Details the options for MCP server configurations AND how to add cluster to MCP
  - MUST refer to the [Database Operations Configuration](steering/mcp-setup.md#cluster-configuration-for-database-operations)
    to correctly add DSQL cluster to MCP configuration
  - Interactive edits when user requests to "Add cluster XYZ to power/mcp" or similar phrase
- **onboarding**
  - SHOULD load when user requests to try the power, "Get started with DSQL" or similar phrase
  - Interactive "Get Started with DSQL" guide for onboarding users step-by-step
- **access-control**
  - MUST load when creating database roles, granting permissions, setting up schemas, or handling sensitive data
  - Scoped role setup, IAM-to-database role mapping, schema separation for sensitive data, role design patterns
- **ddl-migrations**
  - MUST load when performing DROP COLUMN, RENAME COLUMN, ALTER COLUMN TYPE, or DROP CONSTRAINT
  - Table recreation patterns, batched migration for large tables, data validation
- **mysql-to-dsql-migrations**
  - MUST load when migrating from MySQL to DSQL or translating MySQL DDL to DSQL-compatible equivalents
  - MySQL data type mappings, DDL operation translations, AUTO_INCREMENT/ENUM/SET/FOREIGN KEY migration patterns, ALTER TABLE ALTER COLUMN and DROP COLUMN via table recreation

---

## Available MCP Tools

The `aurora-dsql` MCP server provides these tools:

**Database Operations:**
1. **readonly_query** - Execute SELECT queries (returns rows and metadata)
2. **transact** - Execute DDL/DML statements in transaction (takes list of SQL statements)
3. **get_schema** - Get table structure for a specific table

**Documentation & Knowledge:**
4. **dsql_search_documentation** - Search Aurora DSQL documentation
5. **dsql_read_documentation** - Read specific documentation pages
6. **dsql_recommend** - Get DSQL best practice recommendations

---

## Configuration

To use **Database Operations** MCP tools, the DSQL MCP Server REQUIRES an existing DSQL
cluster be correctly added to the MCP configuration to execute these operations atop.
Refer to the provided [MCP Setup Guide](steering/mcp-setup.md), using the
[Cluster-Added MCP Configuration](steering/mcp-setup.md#cluster-configuration-for-database-operations),
to update the power's MCP configuration.

If the user requires complete onboarding guidance in creating a cluster, too,
refere first to the [onboarding guide](steering/onboarding.md).

- **Package:** `awslabs.aurora-dsql-mcp-server@latest`

**Setup Steps:**
1. Create Aurora DSQL cluster in AWS Console
2. Note your cluster identifier from the console
3. Ensure AWS Credentials are configured from CLI: `aws configure`
4. Configure environment variables in MCP server settings:
   - `CLUSTER` - Your DSQL cluster identifier (e.g., "abcdefghijklmnopqrstuvwxyz")
   - `REGION` - AWS region (e.g., "us-east-1")
   - `AWS_PROFILE` - AWS CLI profile (optional)
5. Ensure profile has required IAM permissions:
   - `dsql:DbConnect` - Connect to DSQL cluster
   - `dsql:DbConnectAdmin` - Admin access for DDL operations
6. Test connection with `readonly_query` on `information_schema` as
   detailed in basic operations.

**Database Name:** Always use `postgres` (only database available in DSQL)

---

## Basic Operations

### 1. Schema Exploration
Use `readonly_query` with `information_schema` to list tables and explore database structure. Use
`get_schema` to understand specific table structures including columns, types, and indexes.

### 2. Query Data
Use `readonly_query` for SELECT queries. Always include `tenant_id` in WHERE clause for multi-tenant
applications. Use parameterized queries with `$1, $2` placeholders to prevent SQL injection.

### 3. Execute Schema Changes
Use `transact` tool with a list of SQL statements. Follow one-DDL-per-transaction rule. Always use
`CREATE INDEX ASYNC` in separate transaction. Each DDL operation should be in its own `transact`
call.

### 4. Data Modifications
Use `transact` for INSERT, UPDATE, DELETE operations. Respect transaction limits: 3,000 rows max,
10 MiB max data size, 5 minutes max duration. Batch large operations appropriately.

---

## Common Workflows

### Workflow 1: Create Multi-Tenant Schema

**Goal:** Create a new table with proper tenant isolation and indexing

**Steps:**
1. Create main table with `tenant_id` column using `transact`
2. Create async index on `tenant_id` in separate `transact` call
3. Create composite indexes for common query patterns (separate `transact` calls)
4. Verify schema with `get_schema`

**Critical rules:**
- Include `tenant_id` in all tables
- Use `CREATE INDEX ASYNC` (never synchronous)
- Each DDL in its own `transact` call
- Store arrays/JSON as TEXT

**Example:**
```sql
-- Step 1: Create table
transact([
  "CREATE TABLE entities (
     entity_id VARCHAR(255) PRIMARY KEY,
     tenant_id VARCHAR(255) NOT NULL,
     name VARCHAR(255) NOT NULL
   )"
])

-- Step 2: Create tenant index
transact(["CREATE INDEX ASYNC idx_entities_tenant ON entities(tenant_id)"])

-- Step 3: Verify schema
get_schema("entities")
```

### Workflow 2: Safe Data Migration

**Goal:** Add a new column with defaults safely across all rows

**Steps:**
1. Add column using `transact`: `transact(["ALTER TABLE ... ADD COLUMN ..."])`
2. Populate existing rows with UPDATE in separate `transact` calls (batched under 3,000 rows)
3. Verify migration with `readonly_query` using COUNT
4. Create async index for new column using `transact` if needed

**Critical rules:**
- Add column first, populate later (never add DEFAULT in ALTER TABLE)
- Batch updates under 3,000 rows per transaction
- Each ALTER TABLE in its own transaction
- Verify data before creating indexes

**Example:**
```sql
-- Step 1: Add column
transact(["ALTER TABLE entities ADD COLUMN status VARCHAR(50)"])

-- Step 2: Populate with defaults (batched by tenant)
transact([
  "UPDATE entities
   SET status = 'active'
   WHERE status IS NULL AND tenant_id = $1"
], parameters=["tenant-123"])

-- Step 3: Verify migration
readonly_query(
  "SELECT COUNT(*) as total, COUNT(status) as with_status
   FROM entities
   WHERE tenant_id = $1",
  parameters=["tenant-123"]
)

-- Step 4: Create index
transact(["CREATE INDEX ASYNC idx_entities_status ON entities(tenant_id, status)"])
```

### Workflow 3: Application-Layer Referential Integrity

**Goal:** Safely insert/delete records with parent-child relationships

**Steps for INSERT:**
1. Validate parent exists with `readonly_query`
2. Throw error if parent not found
3. Insert child record using `transact` with parent reference

**Steps for DELETE:**
1. Check for dependent records with `readonly_query` (COUNT)
2. Return error if dependents exist
3. Delete record using `transact` if safe

**Critical rules:**
- Always validate references before mutations
- Check for dependents before deletion
- All checks include `tenant_id` in WHERE clause
- Use parameterized queries

**Example:**
```sql
-- Step 1: Validate parent exists
readonly_query(
  "SELECT entity_id
   FROM entities
   WHERE entity_id = $1 AND tenant_id = $2",
  parameters=["parent-123", "tenant-123"]
)

-- Step 2: If parent exists, insert child
transact([
  "INSERT INTO objectives (objective_id, entity_id, tenant_id, title)
   VALUES ($1, $2, $3, $4)"
], parameters=["obj-456", "parent-123", "tenant-123", "My Objective"])
```

### Workflow 4: Multi-Tenant Query Patterns

**Goal:** Retrieve data scoped to a specific tenant safely

**Steps:**
1. Always include `tenant_id` in WHERE clause
2. Use parameterized queries with validated inputs
3. Execute with `readonly_query`
4. Never allow cross-tenant data access

**Critical rules:**
- ALL queries include `WHERE tenant_id = $1`
- Use parameterized queries (never string interpolation)
- Validate tenant_id before query execution
- Reject cross-tenant access at application layer

**Example:**
```sql
-- Simple tenant-scoped query
readonly_query(
  "SELECT *
   FROM orders
   WHERE tenant_id = $1 AND status = $2",
  parameters=["tenant-123", "active"]
)

-- Aggregation with tenant isolation
readonly_query(
  "SELECT e.name, COUNT(o.order_id) as order_count
   FROM entities e
   LEFT JOIN orders o ON e.entity_id = o.entity_id
   WHERE e.tenant_id = $1
   GROUP BY e.name",
  parameters=["tenant-123"]
)
```

### Workflow 5: Set Up Scoped Database Roles

**Goal:** Create application-specific database roles instead of using the `admin` role

**MUST load [access-control.md](steering/access-control.md) for detailed guidance.**

**Steps:**
1. Connect as `admin` (the only time admin should be used)
2. Create database roles with `CREATE ROLE <name> WITH LOGIN`
3. Create an IAM role with `dsql:DbConnect` for each database role
4. Map database roles to IAM roles with `AWS IAM GRANT`
5. Create dedicated schemas for sensitive data (e.g., `users_schema`)
6. Grant schema and table permissions per role
7. Applications connect using `generate-db-connect-auth-token` (not the admin variant)

**Critical rules:**
- ALWAYS use scoped database roles for application connections
- MUST place user PII and sensitive data in dedicated schemas, not `public`
- ALWAYS use `dsql:DbConnect` for application IAM roles
- SHOULD create separate roles per service component (read-only, read-write, user service, etc.)

### Workflow 6: Table Recreation DDL Migration

**Goal:** Perform DROP COLUMN, RENAME COLUMN, ALTER COLUMN TYPE, or DROP CONSTRAINT using the table recreation pattern.

**MUST load [ddl-migrations.md](steering/ddl-migrations.md) for detailed guidance.**

**Steps:**
1. MUST validate table exists and get row count with `readonly_query`
2. MUST get current schema with `get_schema`
3. MUST create new table with desired structure using `transact`
4. MUST migrate data (batched in 500-1,000 row chunks for tables > 3,000 rows)
5. MUST verify row counts match before proceeding
6. MUST swap tables: drop original, rename new
7. MUST recreate indexes using `CREATE INDEX ASYNC`

**Rules:**
- MUST use batching for tables exceeding 3,000 rows
- PREFER batches of 500-1,000 rows for optimal throughput
- MUST validate data compatibility before type changes (abort if incompatible)
- MUST NOT drop original table until new table is verified
- MUST recreate all indexes after table swap using ASYNC

**Example:**
```sql
-- Step 1: Get current state
readonly_query("SELECT COUNT(*) as total FROM orders")
get_schema("orders")

-- Step 2: Create new table without the column to drop
transact([
  "CREATE TABLE orders_new (
     id UUID PRIMARY KEY,
     tenant_id VARCHAR(255) NOT NULL,
     order_date TIMESTAMP,
     amount DECIMAL(10,2)
   )"
])

-- Step 3: Batch migrate (for large tables, iterate with OFFSET)
transact([
  "INSERT INTO orders_new (id, tenant_id, order_date, amount)
   SELECT id, tenant_id, order_date, amount
   FROM orders
   ORDER BY id
   LIMIT 1000 OFFSET 0"
])

-- Step 4: Verify counts match
readonly_query("SELECT COUNT(*) FROM orders")
readonly_query("SELECT COUNT(*) FROM orders_new")

-- Step 5: Swap tables
transact(["DROP TABLE orders"])
transact(["ALTER TABLE orders_new RENAME TO orders"])

-- Step 6: Recreate indexes
transact(["CREATE INDEX ASYNC idx_orders_tenant ON orders(tenant_id)"])
```

### Workflow 6: MySQL to DSQL Schema Migration

**Goal:** Migrate MySQL table schemas and DDL operations to DSQL-compatible equivalents, including data type mapping, ALTER TABLE ALTER COLUMN, and DROP COLUMN operations.

**MUST load [mysql-to-dsql-migrations.md](steering/mysql-to-dsql-migrations.md) for detailed guidance.**

**Steps:**
1. MUST map all MySQL data types to DSQL equivalents (e.g., AUTO_INCREMENT → UUID/IDENTITY/SEQUENCE, ENUM → VARCHAR with CHECK, JSON → TEXT)
2. MUST remove MySQL-specific features (ENGINE, FOREIGN KEY, ON UPDATE CURRENT_TIMESTAMP, FULLTEXT INDEX)
3. MUST implement application-layer replacements for removed features (referential integrity, timestamp updates)
4. For `ALTER TABLE ... ALTER COLUMN col datatype` or `MODIFY COLUMN`: MUST use table recreation pattern
5. For `ALTER TABLE ... DROP COLUMN col`: MUST use table recreation pattern
6. MUST convert all index creation to `CREATE INDEX ASYNC` in separate transactions
7. MUST validate data compatibility before type changes (abort if incompatible)

**Rules:**
- MUST use table recreation pattern for ALTER COLUMN and DROP COLUMN (not directly supported)
- MUST replace FOREIGN KEY with application-layer referential integrity
- MUST replace ENUM with VARCHAR and CHECK constraint
- MUST replace SET with TEXT (comma-separated)
- MUST replace JSON columns with TEXT
- MUST convert AUTO_INCREMENT to UUID, IDENTITY column, or SEQUENCE (SERIAL not supported)
- MUST replace UNSIGNED integers with CHECK (col >= 0)
- MUST use batching for tables exceeding 3,000 rows
- MUST NOT drop original table until new table is verified

**Example (MySQL CREATE TABLE → DSQL):**
```sql
-- Original MySQL:
-- CREATE TABLE products (
--   id INT AUTO_INCREMENT PRIMARY KEY,
--   name VARCHAR(255) NOT NULL,
--   category ENUM('a','b','c') DEFAULT 'a',
--   metadata JSON,
--   stock INT UNSIGNED DEFAULT 0,
--   FOREIGN KEY (tenant_id) REFERENCES tenants(id)
-- ) ENGINE=InnoDB;

-- Step 1: Create DSQL-compatible table
transact([
  "CREATE TABLE products (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     tenant_id VARCHAR(255) NOT NULL,
     name VARCHAR(255) NOT NULL,
     category VARCHAR(255) DEFAULT 'a' CHECK (category IN ('a', 'b', 'c')),
     metadata TEXT,
     stock INTEGER DEFAULT 0 CHECK (stock >= 0)
   )"
])

-- Step 2: Create indexes (MUST use ASYNC, separate transactions)
transact(["CREATE INDEX ASYNC idx_products_tenant ON products(tenant_id)"])
```

---


## Best Practices

- **SHOULD read guidelines first** - Check [development_guide.md](steering/development-guide.md) before making schema changes
- **SHOULD use preferred language patterns** - Check [language.md](steering/language.md)
- **SHOULD Execute queries directly** - PREFER MCP tools for ad-hoc queries
- **REQUIRED: Follow DDL Guidelines** - Refer to [DDL Rules](steering/development-guide.md#schema-ddl-rules)
- **SHALL repeatedly generate fresh tokens** - Refer to [Connection Limits](steering/development-guide.md#connection-rules)
- **ALWAYS use ASYNC indexes** - `CREATE INDEX ASYNC` is mandatory
- **MUST Serialize arrays/JSON as TEXT** - Store arrays/JSON as TEXT (comma separated, JSON.stringify)
- **ALWAYS Batch under 3,000 rows** - maintain transaction limits
- **REQUIRED: Use parameterized queries** - Prevent SQL injection with $1, $2 placeholders
- **MUST follow correct Application Layer Patterns** - when multi-tenant isolation or application referential itegrity are required; refer to [Application Layer Patterns](steering/development-guide.md#application-layer-patterns)
- **REQUIRED use DELETE for truncation** - DELETE is the only supported operation for truncation
- **SHOULD test any migrations** - Verify DDL on dev clusters before production
- **Plan for Horizontal Scale** - DSQL is designed to optimize for massive scales without latency drops; refer to [Horizontal Scaling](steering/development-guide.md#horizontal-scaling-best-practice)
- **SHOULD use connection pooling in production applications** - Refer to [Connection Pooling](steering/development-guide.md#connection-pooling-recommended)
- **SHOULD debug with the troubleshooting guide:** - Always refer to the resources and guidelines in [troubleshooting.md](steering/troubleshooting.md)
- **ALWAYS use scoped roles for applications** - Create database roles with `dsql:DbConnect`; refer to [Access Control](steering/access-control.md)

---

## Additional Resources

- [Aurora DSQL Documentation](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/)
- [Code Samples Repository](https://github.com/aws-samples/aurora-dsql-samples)
- [PostgreSQL Compatibility](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility.html)
- [IAM Authentication Guide](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/using-database-and-iam-roles.html)
- [CloudFormation Resource](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-dsql-cluster.html)
