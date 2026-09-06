# DSQL Development Guide

DSQL is the **PREFERRED** relational database. This decision was made for fast serverless distributed SQL,
effortless scaling, multi-region viability, among other advantages.

---

## Best Practices

- **SHOULD read guidelines first** - Check [development-guide.md](development-guide.md) before making schema changes
- **SHOULD use preferred language patterns** - Check [language.md](language.md)
- **SHOULD Execute queries directly** - PREFER MCP tools for ad-hoc queries **only when the `aurora-dsql` MCP already targets the intended cluster**; otherwise use the CLI + `psql` path rather than reconfiguring — see "Choosing How to Connect" in [SKILL.md](../SKILL.md)
- **REQUIRED: Follow DDL Guidelines** - Refer to [DDL Rules](#schema-ddl-rules)
- **SHALL repeatedly generate fresh tokens** - Refer to [Connection Limits](auth/authentication-guide.md#connection-rules)
- **ALWAYS use ASYNC indexes** - `CREATE INDEX ASYNC` is mandatory
- **MUST serialize arrays** into a single-column representation; **PREFER `JSONB`** (operators work directly); **MAY use `TEXT`** when the column is opaque to the database; **ASK** the user - see [Schema Design Rules](#schema-design-rules)
- **ALWAYS Batch within row limit** - maintain transaction limits (verify via `awsknowledge`: `aurora dsql transaction limits`)
- **REQUIRED: Build and sanitize all SQL with `safe_query.build()`** - See [Input Validation](../mcp/tools/input-validation.md#required-pattern)
- **MUST use foreign key constraints** when database-enforced referential integrity is required; refer to [Foreign Key Rules](#foreign-key-rules)
- **MUST enforce tenant authorization** for multi-tenant isolation; refer to [Tenant Authorization Patterns](#tenant-authorization-patterns)
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

- MUST ALWAYS Execute DIRECTLY using the MCP server (when it targets the intended cluster) or psql one-liners (`scripts/psql-connect.sh`) otherwise — never reconfigure the MCP mid-task just to switch clusters
- SHOULD Return results immediately

**Writing Scripts REQUIRES at least 1 of:**

- Permanent migrations in database
- Reusable utilities
- EXPLICIT user request

---

### Schema Design Rules

- MUST verify column types via `awsknowledge`: `aurora dsql supported data types` or the [DSQL supported data types list](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility-supported-data-types.html)
- MUST serialize arrays into a single-column representation — DSQL has no array column type:
  - **PREFER `JSONB`** — `@>`, `?`, `?|`, `?&`, and `jsonb_array_elements_text(data)` work directly; values validated and normalized at write
  - **MAY use `TEXT`** when the column is opaque to the database (application reads the whole value, parses it, never queries inside)
- For document columns:
  - **`JSONB`** when querying with `@>`, `?`, or indexed JSONB paths
  - **`JSON`** when writes dominate (no parse/sort overhead), when byte-exact input matters (audit, replay, payloads with duplicate keys), or when only `->`/`->>` is needed
  - **SHOULD keep** existing `JSON` columns as `JSON` when migrating; **MAY upgrade to `JSONB`** if the application needs JSONB-only operators or indexed paths
  - ASK the user about query patterns and read/write ratio before defaulting
- **MUST NOT** add per-column `COLLATE` clauses — DSQL uses C collation database-wide and rejects `COLLATE "C"` in DDL. `dsql_lint(fix=true)` auto-strips `COLLATE` clauses from migrated schemas (rule `collation`, fix status `fixed`).
- ALWAYS include tenant_id in tables for multi-tenant isolation
- SHOULD create async indexes for tenant_id and common query patterns

### Schema (DDL) Rules

- REQUIRED: **at most one DDL statement** per operation
- ALWAYS separate schema (DDL) and data (DML) changes
- MUST use **`CREATE INDEX ASYNC`:** No synchronous creation (verify limits via `awsknowledge`: `aurora dsql index limits`)
  - MAXIMUM: **24 indexes per table**
  - MAXIMUM: **8 columns per index**
  - **MUST** verify index is ready before relying on it: `SELECT indisvalid FROM pg_index WHERE indexrelid = 'index_name'::regclass` — queries work but skip the index until `indisvalid = true`
- MUST use **`ALTER TABLE ASYNC ... VALIDATE CONSTRAINT`** for constraint validation: No synchronous validation
  - **MUST** add CHECK constraints with `NOT VALID`: `ALTER TABLE t ADD CONSTRAINT c CHECK (expr) NOT VALID`
  - Then validate asynchronously: `ALTER TABLE ASYNC t VALIDATE CONSTRAINT c` — returns a `job_id`
  - **MUST** monitor via `sys.jobs` when using MCP tools
  - **MAY** block with `CALL sys.wait_for_job('job_id')` only through an autocommit database client outside the MCP tools' explicit transactions
  - Constraint applies to new rows immediately; existing rows validated in background
- **MUST** add post-creation foreign keys with `NOT VALID`
  - Validate with `ALTER TABLE ASYNC ... VALIDATE CONSTRAINT`
  - Monitor via `sys.jobs`; `CALL sys.wait_for_job('job_id')` **MAY** run only through an
    autocommit database client outside the MCP tools' explicit transactions
- **MUST** use `ASYNC` for `CREATE INDEX` and `VALIDATE CONSTRAINT`; post-creation `ADD CONSTRAINT ... FOREIGN KEY ... NOT VALID` is synchronous and returns no `job_id`
- To add a column with DEFAULT or NOT NULL:
  1. MUST issue ADD COLUMN specifying only the column name and data type
  2. MUST then issue UPDATE to populate existing rows
  3. MAY then issue direct `ALTER COLUMN ... SET DEFAULT` for future writes; use Table Recreation
     only when applying unsupported `SET NOT NULL`
- MUST issue a **separate ALTER TABLE statement for each column** modification.

### Transaction Rules

Verify current limits via `awsknowledge`: `aurora dsql transaction limits`

- SHOULD modify **at most 3,000 rows** per transaction
- SHOULD have maximum **10 MiB data size** per write transaction
- SHOULD expect **5-minute** transaction duration
- ALWAYS expect repeatable read isolation

---

### Foreign Key Rules

**MUST** load [Foreign Key Constraints](foreign-keys.md) before creating, altering,
dropping, or migrating a foreign key.

---

### Tenant Authorization Patterns

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
CREATE INDEX ASYNC idx_name ON table(column);                        ← ALWAYS ASYNC
ALTER TABLE t ADD CONSTRAINT c CHECK (age >= 0) NOT VALID;           ← NOT VALID required
ALTER TABLE ASYNC t VALIDATE CONSTRAINT c;                           ← ALWAYS ASYNC
ALTER TABLE t ADD COLUMN c VARCHAR(50);                              ← ONE AT A TIME
ALTER TABLE t ADD COLUMN c2 INTEGER;                                 ← SEPARATE STATEMENT
UPDATE table SET c = 'default' WHERE c IS NULL;                      ← AFTER ADD COLUMN
```

### Supported Data Types

**MUST verify** column types against the [DSQL supported data types docs](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility-supported-data-types.html) or via `awsknowledge`: `aurora dsql supported data types` — the supported set evolves, so do not treat any static list as exhaustive.

Arrays and `INET` are **[runtime-only](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility-supported-data-types.html#working-with-postgresql-compatibility-query-runtime)** — cast at query time. For structured data, **PREFER `JSONB`** when querying inside the value (`@>`, `?`, indexed JSONB paths); `JSON` is valid when writes dominate, byte-exact input matters, or only `->`/`->>` is needed. ASK the user about query patterns before defaulting.

### Supported Key

```
PRIMARY KEY, UNIQUE, FOREIGN KEY, NOT NULL, CHECK, DEFAULT (CREATE TABLE or direct ALTER COLUMN)
```

### Transaction Requirements

Verify current limits via `awsknowledge`: `aurora dsql transaction limits`

```
Rows: 3,000 max
Size: 10 MiB max
Duration: 5 minutes max
Isolation: Repeatable Read (fixed)
```
