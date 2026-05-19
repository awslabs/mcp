---
name: "amazon-aurora-dsql"
displayName: "Build applications with Aurora DSQL"
description: "Build applications using a serverless, PostgreSQL-compatible database with scale-to-zero and pay-per-use pricing - built for applications at any scale."
keywords: ["aurora", "dsql", "postgresql", "serverless", "database", "sql", "aws", "distributed"]
author: "AWS"
---

# Amazon Aurora DSQL Power

## Overview

The Amazon Aurora DSQL Power provides access to Aurora DSQL, a serverless, PostgreSQL-compatible distributed SQL database. Execute queries, manage schemas, handle migrations, and work with multi-tenant data while respecting DSQL's unique constraints.

**Key capabilities:**
- Direct query execution via MCP tools
- Schema management with DSQL constraints
- Migration support and safe schema evolution
- Multi-tenant isolation patterns
- IAM-based authentication

---

## Available Steering Files

This power includes the following steering files in [steering](./steering)

- **development-guide**
  - ALWAYS load before implementing schema changes or database operations
  - [Best Practices](steering/development-guide.md#best-practices), DDL rules, connection patterns, transaction limits, security best practices
- **input-validation**
  - ALWAYS load before building any SQL query with user-supplied values
  - Validator selection table, [`safe_query.build()`](steering/safe_query.py) required pattern, authorization rules
- **language**
  - MUST load when making language-specific implementation choices. ALWAYS prefer DSQL Connector when available
  - Driver selection, framework patterns, connection code for Python/JS/Go/Java/Rust
- **dsql-examples**
  - CAN load when looking for specific implementation examples
  - Code examples, repository patterns, multi-tenant implementations
- **troubleshooting**
  - SHOULD load when debugging errors or unexpected behavior
  - Common pitfalls, error messages, solutions
- **mcp-setup**
  - ALWAYS load for MCP server configurations or MCP server operations
  - MUST refer to the [Database Operations Configuration](steering/mcp-setup.md#cluster-configuration-for-database-operations)
    to correctly add DSQL cluster to MCP configuration
  - Interactive edits when user requests to "Add cluster XYZ to power/mcp" or similar phrase
- **onboarding**
  - SHOULD load when user requests to try the power, "Get started with DSQL" or similar phrase
  - Interactive "Get Started with DSQL" guide for onboarding users step-by-step
- **access-control**
  - MUST load when creating database roles, granting permissions, setting up schemas, or handling sensitive data
  - Scoped role setup, IAM-to-database role mapping, schema separation for sensitive data, role design patterns
- **ddl-migrations-overview**
  - MUST load when performing DROP COLUMN, ALTER COLUMN TYPE, or DROP CONSTRAINT
  - Table recreation pattern overview, transaction rules, verify & swap pattern
- **ddl-migrations-column-operations**
  - Load for DROP COLUMN, ALTER COLUMN TYPE, SET/DROP NOT NULL, SET/DROP DEFAULT
- **ddl-migrations-constraint-operations**
  - Load for ADD/DROP CONSTRAINT, MODIFY PRIMARY KEY, column split/merge
- **ddl-migrations-batched**
  - Load when migrating tables exceeding 3,000 rows
- **mysql-type-mapping**
  - MUST load when migrating MySQL schemas to DSQL
  - MySQL data type mappings, feature alternatives, DDL operation mapping
- **mysql-ddl-operations**
  - Load when translating MySQL DDL operations to DSQL equivalents
- **mysql-full-example**
  - Load when migrating a complete MySQL table to DSQL
- **query-plan-interpretation**
  - MUST load when diagnosing slow queries or unexpected plans
  - DSQL node types, duration math, estimation-error bands
- **query-plan-catalog-queries**
  - Load alongside interpretation — pg_class/pg_stats/pg_indexes SQL
- **query-plan-guc-experiments**
  - Load alongside interpretation — GUC procedures, >30s skip protocol
- **query-plan-report-format**
  - Load alongside interpretation — required report structure, element checklist
- **auth-guide**
  - SHOULD load when configuring IAM auth or troubleshooting token issues
- **auth-connectivity**
  - Load when setting up connection pooling or connectivity tools
- **auth-scaling**
  - Load when planning connection scaling patterns
- **dsql-lint**
  - SHOULD load when validating SQL for DSQL compatibility or migrating schemas
  - `dsql_lint` MCP tool reference, fix statuses, workflow steps, ORM integration, unfixable error resolution, error handling

---

## Available MCP Tools

The `aurora-dsql` MCP server provides these tools:

**Database Operations:**
1. **readonly_query** - Execute SELECT queries (returns rows and metadata)
2. **transact** - Execute DDL/DML statements in transaction (takes list of SQL statements)
3. **get_schema** - Get table structure for a specific table

**SQL Validation:**
4. **dsql_lint** - Validate SQL for DSQL compatibility and optionally auto-fix issues. Use before executing externally-sourced SQL.

**Documentation & Knowledge:**
4. **dsql_search_documentation** - Search Aurora DSQL documentation
5. **dsql_read_documentation** - Read specific documentation pages
6. **dsql_recommend** - Get DSQL best practice recommendations

---

## Configuration

To use **Database Operations** MCP tools, the DSQL MCP Server REQUIRES an existing DSQL
cluster be correctly added to the MCP configuration.
Refer to the provided [MCP Setup Guide](steering/mcp-setup.md), using the
[Cluster-Added MCP Configuration](steering/mcp-setup.md#cluster-configuration-for-database-operations),
to update the power's MCP configuration.

- **Package:** `awslabs.aurora-dsql-mcp-server@latest`

**Setup Steps:**
1. Create Aurora DSQL cluster in AWS Console
2. Note your cluster identifier from the console
3. Ensure AWS Credentials are configured from CLI: `aws configure`
4. Configure environment variables in MCP server settings:
   - `CLUSTER` - Your DSQL cluster identifier
   - `REGION` - AWS region (e.g., "us-east-1")
   - `AWS_PROFILE` - AWS CLI profile (optional)
5. Ensure profile has required IAM permissions:
   - `dsql:DbConnect` - Connect to DSQL cluster
   - `dsql:DbConnectAdmin` - Admin access for DDL operations
6. Test connection with `readonly_query` on `information_schema`

**Database Name:** Always use `postgres` (only database available in DSQL)

---

## Input Validation

The `readonly_query` and `transact` tools accept only SQL strings — no parameter
binding. **MUST** build every SQL string with [`safe_query.build()`](steering/safe_query.py).
See [input-validation.md](steering/input-validation.md) for the required pattern and
validator selection table.

```python
from safe_query import build, allow, regex, ident, literal, TENANT_SLUG, UUID

sql = build(
    "SELECT * FROM {tbl} WHERE tenant_id = {tid} AND entity_id = {eid}",
    tbl=ident("entities"),
    tid=regex(tenant_id, TENANT_SLUG),
    eid=regex(entity_id, UUID),
)
readonly_query(sql)
```

`build()` raises `UnsafeSQLError` when a placeholder receives a raw string, so
`build("... {x} ...", x=user_input)` fails loudly at the call site.

Authorize the caller against the tenant **before** validating format or calling `build()`.

---

## Common Workflows

### Workflow 1: Create Multi-Tenant Schema

1. Create main table with `tenant_id` column using `transact`
2. Create async index on `tenant_id` in separate `transact` call
3. Create composite indexes for common query patterns (separate `transact` calls)
4. Verify schema with `get_schema`

- **MUST** include `tenant_id` in all tables
- **MUST** use `CREATE INDEX ASYNC` exclusively
- **MUST** issue each DDL in its own `transact` call
- **MUST** store arrays/JSON as TEXT

### Workflow 2: Safe Data Migration

1. Validate DDL with `dsql_lint(sql=..., fix=true)` — apply fixes if needed
2. Add column using `transact`: `transact(["ALTER TABLE ... ADD COLUMN ..."])`
3. Populate existing rows with UPDATE in separate `transact` calls (batched under 3,000 rows)
4. Verify migration with `readonly_query` using COUNT
5. Create async index for new column using `transact` if needed

- **MUST** validate DDL with `dsql_lint` before executing
- **MUST** add column first, populate later
- **MUST** issue ADD COLUMN with only name and type; apply DEFAULT via separate UPDATE
- **MUST** batch updates under 3,000 rows in separate `transact` calls

### Workflow 3: Application-Layer Referential Integrity

**INSERT:** Validate parent exists with `readonly_query` → throw error if not found → insert child with `transact`.

**DELETE:** Check dependents with `readonly_query` COUNT → return error if dependents exist → delete with `transact` if safe.

### Workflow 4: Query with Tenant Isolation

1. **MUST** authorize the caller against the tenant — format validation does not establish authorization
2. **MUST** build SQL with [`safe_query.build()`](steering/safe_query.py) — use `allow()`/`regex()` for
   values (emits `'v'`), `ident()` for table/column names (emits `"v"`).
   See [input-validation.md](steering/input-validation.md)
3. **MUST** include `tenant_id` in the WHERE clause; reject cross-tenant access at the application layer

### Workflow 5: Set Up Scoped Database Roles

**MUST** load [access-control.md](steering/access-control.md) for role setup, IAM mapping, and schema permissions.

### Workflow 6: Table Recreation DDL Migration

DSQL does NOT support direct `ALTER COLUMN TYPE`, `DROP COLUMN`, `DROP CONSTRAINT`, or `MODIFY PRIMARY KEY`. These require the **Table Recreation Pattern**. This is a destructive workflow that requires user confirmation at each step. Validate the new CREATE TABLE with `dsql_lint(sql=..., fix=true)` before execution.

**MUST** load [ddl-migrations-overview.md](steering/ddl-migrations-overview.md) before attempting any of these operations.

### Workflow 7: Validate and Migrate to DSQL

Run `dsql_lint(sql=source_sql, fix=true)` to validate and auto-convert PostgreSQL-compatible SQL. For MySQL-specific syntax (SET, ENGINE, PARTITION BY), `dsql_lint` returns a parse error — fall back to [mysql-type-mapping.md](steering/mysql-type-mapping.md) for manual conversion. **MUST** load [dsql-lint.md](steering/dsql-lint.md) for the full workflow, ORM-specific guidance, and unfixable error resolution.

### Workflow 8: Query Plan Explainability

Explains why the DSQL optimizer chose a particular plan. Triggered by slow queries, high DPU, unexpected Full Scans, or plans the user doesn't understand.

**MUST** load [query-plan-interpretation.md](steering/query-plan-interpretation.md) plus the three companion files (catalog-queries, guc-experiments, report-format) before starting.

---

## Error Scenarios

- **OCC serialization error:** Retry the transaction. If persistent, check for hot-key contention — see [troubleshooting.md](steering/troubleshooting.md).
- **Transaction exceeds limits:** Split into batches under 3,000 rows — see [ddl-migrations-batched.md](steering/ddl-migrations-batched.md).
- **Token expiration mid-operation:** Generate a fresh IAM token — see [auth-guide.md](steering/auth-guide.md).

---

## Additional Resources

- [Aurora DSQL Documentation](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/)
- [Code Samples Repository](https://github.com/aws-samples/aurora-dsql-samples)
- [PostgreSQL Compatibility](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility.html)
- [CloudFormation Resource](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-dsql-cluster.html)
