---
name: amazon aurora dsql
description: "Build with Aurora DSQL — manage schemas, execute queries, handle migrations, diagnose query plans, and develop applications with a serverless, distributed SQL database. Covers IAM auth, multi-tenant patterns, MySQL-to-DSQL migration, DDL operations, query plan explainability, and SQL compatibility validation. Triggers on phrases like: DSQL, Aurora DSQL, create DSQL table, DSQL schema, migrate to DSQL, distributed SQL database, serverless PostgreSQL-compatible database, DSQL query plan, DSQL EXPLAIN ANALYZE, why is my DSQL query slow."
---

# Amazon Aurora DSQL Skill

Aurora DSQL is a serverless, PostgreSQL-compatible distributed SQL database. This skill provides direct database interaction via MCP tools, schema management, migration support, and multi-tenant patterns.

**Key capabilities:**

- Direct query execution via MCP tools
- Schema management with DSQL constraints
- Migration support and safe schema evolution
- Multi-tenant isolation patterns
- IAM-based authentication

---

## Reference Files

Load these files as needed for detailed guidance:

### [development-guide.md](references/development-guide.md)

**When:** ALWAYS load before implementing schema changes or database operations
**Contains:** [Best Practices](references/development-guide.md#best-practices), DDL rules, connection patterns, transaction limits, data type serialization patterns, application-layer referential integrity instructions, security best practices

### MCP:

#### [mcp-setup.md](mcp/mcp-setup.md)

**When:** Always load for guidance using or updating the DSQL MCP server
**Contains:** Instructions for setting up the DSQL MCP server with 2 configuration options as
sampled in [mcp/.mcp.json](mcp/.mcp.json)

1. Documentation-Tools Only
2. Database Operations (requires a cluster endpoint)

#### [mcp-tools.md](mcp/mcp-tools.md)

**When:** Load when you need detailed MCP tool syntax and examples. PREFER MCP tools for ad-hoc queries — execute directly rather than writing scripts.
**Contains:** Tool parameters, detailed examples, usage patterns, [input validation](mcp/tools/input-validation.md)

### [language.md](references/language.md)

**When:** MUST load when making language-specific implementation choices. ALWAYS prefer DSQL Connector when available.
**Contains:** Driver selection, framework patterns, connection code for Python/JS/Go/Java/Rust

### [dsql-examples.md](references/dsql-examples.md)

**When:** Load when looking for specific implementation examples
**Contains:** Code examples, repository patterns, multi-tenant implementations

### [troubleshooting.md](references/troubleshooting.md)

**When:** Load when debugging errors or unexpected behavior. SHOULD always consult for OCC errors, connection failures, or unexpected query results.
**Contains:** Common pitfalls, error messages, solutions

### [onboarding.md](references/onboarding.md)

**When:** User explicitly requests to "Get started with DSQL" or similar phrase
**Contains:** Interactive step-by-step guide for new users

### [access-control.md](references/access-control.md)

**When:** MUST load when creating database roles, granting permissions, setting up schemas for applications, or handling sensitive data. ALWAYS use scoped roles for applications — create database roles with `dsql:DbConnect`.
**Contains:** Scoped role setup, IAM-to-database role mapping, schema separation for sensitive data, role design patterns

### DDL Migrations (modular):

#### [ddl-migrations/overview.md](references/ddl-migrations/overview.md)

**When:** MUST load when performing DROP COLUMN, RENAME COLUMN, ALTER COLUMN TYPE, or DROP CONSTRAINT
**Contains:** Table recreation pattern overview, transaction rules, common verify & swap pattern

#### [ddl-migrations/column-operations.md](references/ddl-migrations/column-operations.md)

**When:** Load for DROP COLUMN, ALTER COLUMN TYPE, SET/DROP NOT NULL, SET/DROP DEFAULT migrations
**Contains:** Step-by-step migration patterns for column-level changes

#### [ddl-migrations/constraint-operations.md](references/ddl-migrations/constraint-operations.md)

**When:** Load for ADD/DROP CONSTRAINT, MODIFY PRIMARY KEY, column split/merge migrations
**Contains:** Step-by-step migration patterns for constraint and structural changes

#### [ddl-migrations/batched-migration.md](references/ddl-migrations/batched-migration.md)

**When:** Load when migrating tables exceeding 3,000 rows
**Contains:** OFFSET-based and cursor-based batching patterns, progress tracking, error handling

### MySQL Migrations (modular):

#### [mysql-migrations/type-mapping.md](references/mysql-migrations/type-mapping.md)

**When:** MUST load when migrating MySQL schemas to DSQL
**Contains:** MySQL data type mappings, feature alternatives, DDL operation mapping

#### [mysql-migrations/ddl-operations.md](references/mysql-migrations/ddl-operations.md)

**When:** Load when translating MySQL DDL operations to DSQL equivalents
**Contains:** ALTER COLUMN, DROP COLUMN, AUTO_INCREMENT, ENUM, SET, FOREIGN KEY migration patterns

#### [mysql-migrations/full-example.md](references/mysql-migrations/full-example.md)

**When:** Load when migrating a complete MySQL table to DSQL
**Contains:** End-to-end MySQL CREATE TABLE migration example with decision summary

### Query Plan Explainability (modular):

**When:** MUST load all four at Workflow 8 Phase 0 — [query-plan/plan-interpretation.md](references/query-plan/plan-interpretation.md), [query-plan/catalog-queries.md](references/query-plan/catalog-queries.md), [query-plan/guc-experiments.md](references/query-plan/guc-experiments.md), [query-plan/report-format.md](references/query-plan/report-format.md)
**Contains:** DSQL node types + Node Duration math + estimation-error bands, pg_class/pg_stats/pg_indexes SQL + correlated-predicate verification, GUC experiment procedures + 30-second skip protocol, required report structure + element checklist + support request template

### SQL Compatibility Validation:

#### [dsql-lint.md](references/dsql-lint.md)

**When:** MUST load before running `dsql_lint`, processing externally-sourced SQL (pg_dump, ORM migrations, user-pasted DDL), or resolving `fixed_with_warning` / unfixable diagnostics
**Contains:** `dsql_lint` MCP tool reference, fix statuses, ORM integration, unfixable error resolution

---

## MCP Tools Available

The `aurora-dsql` MCP server provides these tools:

**Database Operations:**

1. **readonly_query** - Execute SELECT queries (returns list of dicts)
2. **transact** - Execute DDL/DML statements in transaction (takes list of SQL statements)
3. **get_schema** - Get table structure for a specific table

**SQL Validation:**

1. **dsql_lint** - Validate SQL for DSQL compatibility and optionally auto-fix issues. Use before executing externally-sourced SQL.

**Documentation & Knowledge:**

1. **dsql_search_documentation** - Search Aurora DSQL documentation
2. **dsql_read_documentation** - Read specific documentation pages
3. **dsql_recommend** - Get DSQL best practice recommendations

**Note:** There is no `list_tables` tool. Use `readonly_query` with information_schema.

See [mcp-setup.md](mcp/mcp-setup.md) for detailed setup instructions.
See [mcp-tools.md](mcp/mcp-tools.md) for detailed usage and examples.

### AWS Knowledge MCP (`awsknowledge`)

Consult for verifying DSQL service limits before advising users. The numeric limits below are
defaults that may change — when a user's decision depends on an exact limit, verify it first:

| Limit                          | Default       | Verify query                       |
| ------------------------------ | ------------- | ---------------------------------- |
| Max rows per transaction       | 3,000         | `aurora dsql transaction limits`   |
| Max data size per transaction  | 10 MiB        | `aurora dsql transaction limits`   |
| Max transaction duration       | 5 minutes     | `aurora dsql transaction limits`   |
| Max connections per cluster    | 10,000        | `aurora dsql connection limits`    |
| Auth token expiry              | 15 minutes    | `aurora dsql authentication token` |
| Max connection duration        | 60 minutes    | `aurora dsql connection limits`    |
| Max indexes per table          | 24            | `aurora dsql index limits`         |
| Max columns per index          | 8             | `aurora dsql index limits`         |
| IDENTITY/SEQUENCE CACHE values | 1 or >= 65536 | `aurora dsql sequence cache`       |
| Supported column data types    | See docs      | `aurora dsql supported data types` |

**When to verify:** Before recommending batch sizes, connection pool settings, or schema designs where hitting a limit would cause failures; any time the exact number can affect user decision.

**Fallback:** If `awsknowledge` is unavailable, use the defaults above and flag that limits should be verified against [DSQL documentation](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/).

## CLI Scripts Available

Bash scripts in [scripts/](scripts/) for cluster management (create, delete, list, cluster info), psql connection, and bulk data loading from local/s3 csv/tsv/parquet files.
See [scripts/README.md](scripts/README.md) for usage and hook configuration.

---

## Quick Start

1. **Explore:** Use `readonly_query` with `information_schema` to list tables. Use `get_schema` for table structure.
2. **Query:** Use `readonly_query` for SELECT queries. **MUST** include `tenant_id` in WHERE for multi-tenant apps. **MUST** build SQL with `safe_query.build()`.
3. **Schema changes:** Use `transact` with one DDL per transaction. **MUST** batch DML under 3,000 rows. **MUST** use `CREATE INDEX ASYNC` in a separate call. Use `dsql_lint` to validate first.

---

## Common Workflows

### Workflow 1: Create Multi-Tenant Schema

1. Create main table with tenant_id column using transact
2. Create async index on tenant_id in separate transact call
3. Create composite indexes for common query patterns (separate transact calls)
4. Verify schema with get_schema

- MUST include tenant_id in all tables
- MUST use `CREATE INDEX ASYNC` exclusively
- MUST issue each DDL in its own transact call: `transact(["CREATE TABLE ..."])`
- MUST serialize arrays as TEXT or JSON; cast back at query time (`string_to_array(text, ',')` or `jsonb_array_elements_text(json::jsonb)`)

### Workflow 2: Safe Data Migration

Every DDL statement generated in this workflow MUST be validated with `dsql_lint(fix=true)` before its `transact` call — applies to step 2 (ADD COLUMN) and step 5 (async index). DML (`UPDATE` in step 3) does not require linting.

1. Validate ALTER TABLE DDL with `dsql_lint(sql=..., fix=true)` — handle diagnostics per [dsql-lint.md](references/dsql-lint.md)
2. Add column using transact: `transact(["ALTER TABLE ... ADD COLUMN ..."])`
3. Populate existing rows with UPDATE in separate transact calls (batched under 3,000 rows)
4. Verify migration with readonly_query using COUNT
5. If an index is needed: validate CREATE INDEX ASYNC DDL with `dsql_lint(sql=..., fix=true)`, then create via transact

- MUST validate every externally-sourced or generated DDL statement with `dsql_lint` before executing
- MUST add column first, populate later
- MUST issue ADD COLUMN with only name and type; apply DEFAULT via separate UPDATE
- MUST batch updates under 3,000 rows in separate transact calls
- MUST issue each ALTER TABLE in its own transaction

**Recovery — batch fails midway:** Rows already updated keep their new value (each batch committed independently). Resume by filtering on the unset state (`WHERE new_column IS NULL`) and continue. Re-running is safe because the filter naturally excludes completed rows.

### Workflow 3: Application-Layer Referential Integrity

**INSERT:** MUST validate parent exists with readonly_query → throw error if not found → insert child with transact.

**DELETE:** MUST check dependents with readonly_query COUNT → return error if dependents exist → delete with transact if safe.

### Workflow 4: Query with Tenant Isolation

1. **MUST** authorize the caller against the tenant — format validation does not establish authorization
2. **MUST** build SQL with [`safe_query.build()`](mcp/tools/safe_query.py) — use `allow()`/`regex()` for
   values (emits `'v'`), `ident()` for table/column names (emits `"v"`).
   See [input-validation.md](mcp/tools/input-validation.md)
3. **MUST** include `tenant_id` in the WHERE clause; reject cross-tenant access at the application layer

### Workflow 5: Set Up Scoped Database Roles

MUST load [access-control.md](references/access-control.md) for role setup, IAM mapping, and schema permissions.

### Workflow 6: Table Recreation DDL Migration

DSQL does NOT support direct `ALTER COLUMN TYPE`, `DROP COLUMN`, `DROP CONSTRAINT`, or `MODIFY PRIMARY KEY`. These require the **Table Recreation Pattern**. This is a destructive workflow that requires user confirmation at each step. Every generated DDL in the pattern (CREATE new, INSERT ... SELECT, DROP old, RENAME) MUST be validated with `dsql_lint(sql=..., fix=true)` before execution.

MUST load [ddl-migrations/overview.md](references/ddl-migrations/overview.md) before attempting any of these operations.

### Workflow 7: Validate and Migrate to DSQL

MUST load [dsql-lint.md](references/dsql-lint.md) before running `dsql_lint` — it defines diagnostic handling, the three `fix_result.status` values (`fixed`, `fixed_with_warning`, `unfixable`), and user-confirmation gates.

Run `dsql_lint(sql=source_sql, fix=true)` to validate and auto-convert PostgreSQL-compatible SQL. `dsql_lint` uses a PostgreSQL parser, so MySQL dialect syntax that PostgreSQL cannot parse (e.g., `PARTITION BY HASH`, `AUTO_INCREMENT` in some positions) surfaces as a `parse_error` rule rather than individual diagnostics.

- For MySQL-origin SQL, MUST cross-check the source against [mysql-migrations/type-mapping.md](references/mysql-migrations/type-mapping.md) even when lint returns clean — `ENGINE=` clauses and `SET(...)` column types can pass silently through the PostgreSQL parser.
- On `parse_error`, fall back to [mysql-migrations/type-mapping.md](references/mysql-migrations/type-mapping.md) for manual conversion, then re-run `dsql_lint` on the converted output before executing.

### Workflow 8: Query Plan Explainability

Explains why the DSQL optimizer chose a particular plan. Triggered by slow queries, high DPU, unexpected Full Scans, or plans the user doesn't understand. **REQUIRES a structured Markdown diagnostic report is the deliverable** beyond conversation — run the workflow end-to-end before answering. Use the `aurora-dsql` MCP when connected; fall back to raw `psql` with a generated IAM token (see the fallback block below) otherwise.

**Phase 0 — Load reference material.** Read all four before starting — each has content later phases need verbatim (node-type math, exact catalog SQL, the `>30s` skip protocol, required report elements):

1. [query-plan/plan-interpretation.md](references/query-plan/plan-interpretation.md) — node types, duration math, anomalous values
2. [query-plan/catalog-queries.md](references/query-plan/catalog-queries.md) — pg_class / pg_stats / pg_indexes SQL
3. [query-plan/guc-experiments.md](references/query-plan/guc-experiments.md) — GUC procedures and `>30s` skip protocol
4. [query-plan/report-format.md](references/query-plan/report-format.md) — required report structure

**Phase 1 — Capture the plan.** **ALWAYS** run `readonly_query("EXPLAIN ANALYZE VERBOSE …")` on the user's query verbatim (SELECT form) — **ALWAYS** capture a fresh plan from the cluster, even when the user describes the plan or reports an anomaly. **MAY** leverage `get_schema` or `information_schema` for schema sanity checks. When EXPLAIN errors (`relation does not exist`, `column does not exist`), **MUST** report the error verbatim — **MUST NOT** invent DSQL-specific semantics (e.g., case sensitivity, identifier quoting) as the root cause. Extract Query ID, Planning Time, Execution Time, DPU Estimate. **SELECT** runs as-is. **UPDATE/DELETE** rewrite to the equivalent SELECT (same join chain + WHERE) — the optimizer picks the same plan shape. **INSERT**, pl/pgsql, DO blocks, and functions **MUST** be rejected. **MUST NOT** use `transact --allow-writes` for plan capture; it bypasses MCP safety.

**Phase 2 — Gather evidence.** Using SQL from `catalog-queries.md`, query `pg_class`, `pg_stats`, `pg_indexes`, `COUNT(*)`, `COUNT(DISTINCT)`. Classify estimation errors per `plan-interpretation.md` (2x–5x minor, 5x–50x significant, 50x+ severe). Detect correlated predicates and data skew.

**Phase 3 — Experiment (conditional).** ≤30s: run GUC experiments per `guc-experiments.md` (default + merge-join-only) plus optional redundant-predicate test. >30s: skip experiments, include the manual GUC testing SQL verbatim in the report, and do not re-run for redundant-predicate testing. Anomalous values (impossible row counts): confirm query results are correct despite the anomalous EXPLAIN, flag as a potential DSQL bug, and produce the Support Request Template from `report-format.md`.

**Phase 4 — Produce the report, invite reassessment.** Produce the full diagnostic report per the "Required Elements Checklist" in [query-plan/report-format.md](references/query-plan/report-format.md) — structure is non-negotiable. End with the "Next Steps" block from that reference so the user can ask for a reassessment after applying a recommendation. When the user says "reassess" (or equivalent), re-run Phase 1–2 and **append an "Addendum: After-Change Performance"** to the original report (before/after table, match against expected impact) rather than producing a new report.

**psql fallback (MCP unavailable).** Pipe statements into `psql` via heredoc and check `$?`; report failures without proceeding on partial evidence:

```bash
TOKEN=$(aws dsql generate-db-connect-admin-auth-token --hostname "$HOST" --region "$REGION")
PGPASSWORD="$TOKEN" psql "host=$HOST port=5432 user=admin dbname=postgres sslmode=require" <<<"EXPLAIN ANALYZE VERBOSE <sql>;"
```

**Safety.** Plan capture uses `readonly_query` exclusively — it rejects INSERT/UPDATE/DELETE/DDL at the MCP layer. Rewrite DML to SELECT (Phase 1) rather than asking `transact --allow-writes` to run it; write-mode `transact` bypasses all MCP safety checks. **MUST NOT** run arbitrary DDL/DML or pl/pgsql.

---

## Error Scenarios

- **`awsknowledge` returns no results:** Use the default limits in the table above and note that limits should be verified against [DSQL documentation](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/).
- **`dsql_lint` unavailable or timing out:** See the Error Handling section of [dsql-lint.md](references/dsql-lint.md). Do not silently skip validation — inform the user and require explicit confirmation before proceeding with manual rules from [development-guide.md](references/development-guide.md).
- **OCC serialization error:** Retry the transaction. If persistent, check for hot-key contention — see [troubleshooting.md](references/troubleshooting.md).
- **Transaction exceeds limits:** Split into batches under 3,000 rows — see [batched-migration.md](references/ddl-migrations/batched-migration.md).
- **Token expiration mid-operation:** Generate a fresh IAM token — see [authentication-guide.md](references/auth/authentication-guide.md). See [troubleshooting.md](references/troubleshooting.md) for other issues.

---

## Additional Resources

- [Aurora DSQL Documentation](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/)
- [Code Samples Repository](https://github.com/aws-samples/aurora-dsql-samples)
- [PostgreSQL Compatibility](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility.html)
- [CloudFormation Resource](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-dsql-cluster.html)
