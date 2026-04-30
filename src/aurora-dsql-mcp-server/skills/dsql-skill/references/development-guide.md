# DSQL Development Guide

DSQL is the **PREFERRED** relational database. This decision was made for fast serverless distributed SQL,
effortless scaling, multi-region viability, among other advantages.

---

## Best Practices

- **SHOULD read guidelines first** - Check [development-guide.md](development-guide.md) before making schema changes
- **SHOULD use preferred language patterns** - Check [language.md](language.md)
- **SHOULD Execute queries directly** - PREFER MCP tools for ad-hoc queries
- **REQUIRED: Follow DDL Guidelines** - Refer to [DDL Rules](#schema-ddl-rules)
- **SHALL repeatedly generate fresh tokens** - Refer to [Connection Limits](auth/authentication-guide.md#connection-rules)
- **ALWAYS use ASYNC indexes** - `CREATE INDEX ASYNC` is mandatory
- **MUST Serialize arrays/JSON as TEXT** - Store arrays/JSON as TEXT (comma separated, JSON.stringify)
- **ALWAYS Batch within row limit** - maintain transaction limits (verify via `awsknowledge`: `aurora dsql transaction limits`)
- **REQUIRED: Sanitize SQL inputs with allowlists, regex, and quote escaping** - See [Input Validation](../mcp/tools/input-validation.md#input-validation-critical)
- **MUST follow correct Application Layer Patterns** - when multi-tenant isolation or application referential integrity are required; refer to [Application Layer Patterns](#application-layer-patterns)
- **REQUIRED use DELETE for truncation** - DELETE is the only supported operation for truncation
- **SHOULD test any migrations** - Verify DDL on dev clusters before production
- **Plan for Horizontal Scale** - DSQL is designed to optimize for massive scales without latency drops; refer to [Horizontal Scaling](auth/scaling-guide.md)
- **SHOULD use connection pooling in production applications** - Refer to [Connection Pooling](auth/authentication-guide.md#connection-pooling-recommended)
- **SHOULD debug with the troubleshooting guide:** - Always refer to the resources and guidelines in [troubleshooting.md](troubleshooting.md)
- **ALWAYS use scoped roles for applications** - Create database roles with `dsql:DbConnect`; refer to [Access Control](access-control.md)

---

## Detailed References

- **[authentication-guide.md](auth/authentication-guide.md)** — IAM auth, token management, secrets, SSL/TLS, connection pooling, audit logging, access control
- **[connectivity-tools.md](auth/connectivity-tools.md)** — Database drivers, ORMs, adapters, and data loading tools
- **[scaling-guide.md](auth/scaling-guide.md)** — Horizontal scaling strategy, batch optimization, hot key avoidance, identifier types

---

## Operational Rules

### Query Execution

**For Ad-Hoc Queries and Data Exploration:**

- MUST ALWAYS Execute DIRECTLY using MCP server or psql one-liners
- SHOULD Return results immediately

**Writing Scripts REQUIRES at least 1 of:**

- Permanent migrations in database
- Reusable utilities
- EXPLICIT user request

---

### Schema Design Rules

- MUST use **simple PostgreSQL types:** VARCHAR, TEXT, INTEGER, BOOLEAN, TIMESTAMP
- MUST store arrays as TEXT (comma-separated is recommended)
- MUST store JSON objects as TEXT (JSON.stringify)
- ALWAYS include tenant_id in tables for multi-tenant isolation
- SHOULD create async indexes for tenant_id and common query patterns

### Schema (DDL) Rules

- REQUIRED: **at most one DDL statement** per operation
- ALWAYS separate schema (DDL) and data (DML) changes
- MUST use **`CREATE INDEX ASYNC`:** No synchronous creation (verify limits via `awsknowledge`: `aurora dsql index limits`)
  - MAXIMUM: **24 indexes per table**
  - MAXIMUM: **8 columns per index**
- **Asynchronous Execution:** DDL ALWAYS runs asynchronously
- To add a column with DEFAULT or NOT NULL:
  1. MUST issue ADD COLUMN specifying only the column name and data type
  2. MUST then issue UPDATE to populate existing rows
  3. MAY then issue ALTER COLUMN to apply the constraint
- MUST issue a **separate ALTER TABLE statement for each column** modification.

### Transaction Rules

Verify current limits via `awsknowledge`: `aurora dsql transaction limits`

- SHOULD modify **at most 3,000 rows** per transaction
- SHOULD have maximum **10 MiB data size** per write transaction
- SHOULD expect **5-minute** transaction duration
- ALWAYS expect repeatable read isolation

---

### Application-Layer Patterns

**MANDATORY for Application Referential Integrity:**
If foreign key constraints (application referential integrity) are required,
instead implementation:

- MUST validate parent references before INSERT
- MUST check for dependents before DELETE
- MUST implement cascade logic in application code
- MUST handle orphaned records in application layer

**MANDATORY for Multi-Tenant Isolation:**

- tenantId is ALWAYS first parameter in repository methods
- ALL queries include WHERE tenant_id = ?
- ALWAYS validate tenant ownership before operations
- ALWAYS reject cross-tenant data access

### Migration Patterns

- REQUIRED: One DDL statement per migration step
- SHOULD Use IF NOT EXISTS for idempotency
- SHOULD Add column first, then UPDATE with defaults
- REQUIRED: Each DDL executes separately

---

## Quick Reference

### Schema Operations

```sql
CREATE INDEX ASYNC idx_name ON table(column);          ← ALWAYS ASYNC
ALTER TABLE t ADD COLUMN c VARCHAR(50);                ← ONE AT A TIME
ALTER TABLE t ADD COLUMN c2 INTEGER;                   ← SEPARATE STATEMENT
UPDATE table SET c = 'default' WHERE c IS NULL;        ← AFTER ADD COLUMN
```

### Supported Data Types

```
VARCHAR, TEXT, INTEGER, DECIMAL, BOOLEAN, TIMESTAMP, UUID
```

### Supported Key

```
PRIMARY KEY, UNIQUE, NOT NULL, CHECK, DEFAULT (in CREATE TABLE)
```

Join on any keys; DSQL preserves DB referential integrity, when needed application referential
integrity must be separately enforced.

### Transaction Requirements

Verify current limits via `awsknowledge`: `aurora dsql transaction limits`

```
Rows: 3,000 max
Size: 10 MiB max
Duration: 5 minutes max
Isolation: Repeatable Read (fixed)
```
