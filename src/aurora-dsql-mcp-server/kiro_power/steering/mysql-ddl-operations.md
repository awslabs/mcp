# MySQL to DSQL Migration: DDL Operations

Migration patterns for specific MySQL DDL operations to DSQL-compatible equivalents.

**MUST read [type-mapping.md](type-mapping.md) first** for data type mappings and the CRITICAL Destructive Operations Warning.
**MUST read [ddl-migrations/overview.md](../ddl-migrations/overview.md)** for the general Table Recreation Pattern and user verification requirements.

---

## Table Recreation Pattern Overview

MUST follow this sequence with user verification at each step:

1. **Plan & Confirm** - MUST present migration plan and obtain user approval to proceed
2. **Validate** - Check data compatibility with new structure; MUST report findings to user
3. **Create** - Create new table with desired structure; MUST verify with user before execution
4. **Migrate** - Copy data (batched for tables > 3,000 rows); MUST report progress to user
5. **Verify** - Confirm row counts match; MUST present comparison to user
6. **Swap** - CRITICAL: MUST obtain explicit user confirmation before DROP TABLE
7. **Re-index** - Recreate indexes using ASYNC; MUST confirm completion with user

### Transaction Rules

- **MUST batch** migrations exceeding 3,000 row mutations
- **PREFER batches of 500-1,000 rows** for optimal throughput
- **MUST respect** 10 MiB data size per transaction
- **MUST respect** 5-minute transaction duration

---

## Common Verify & Swap Pattern

All migrations end with this pattern (referenced in examples below).

**CRITICAL: MUST obtain explicit user confirmation before DROP TABLE step.**

```sql
-- MUST verify counts match
readonly_query("SELECT COUNT(*) FROM target_table")
readonly_query("SELECT COUNT(*) FROM target_table_new")

-- CHECKPOINT: MUST present count comparison to user and obtain confirmation
-- Agent MUST display: "Original table has X rows, new table has Y rows.
-- Proceeding will DROP the original table. This action is IRREVERSIBLE.
-- Do you want to proceed? (yes/no)"
-- MUST NOT proceed without explicit "yes" confirmation

-- MUST swap tables (DESTRUCTIVE - requires user confirmation above)
transact(["DROP TABLE target_table"])
transact(["ALTER TABLE target_table_new RENAME TO target_table"])

-- MUST recreate indexes
transact(["CREATE INDEX ASYNC idx_target_tenant ON target_table(tenant_id)"])
```

---

## Detailed Migration Patterns

Load the relevant file for the specific MySQL DDL operation you need to migrate:

- **[ddl-column-changes.md](ddl-column-changes.md)** — ALTER COLUMN type, DROP COLUMN
- **[ddl-auto-increment.md](ddl-auto-increment.md)** — AUTO_INCREMENT to UUID/IDENTITY/SEQUENCE
- **[ddl-type-alternatives.md](ddl-type-alternatives.md)** — ENUM, SET, ON UPDATE CURRENT_TIMESTAMP, FOREIGN KEY
- **[ddl-constraints.md](ddl-constraints.md)** — SET/DROP NOT NULL, SET/DROP DEFAULT
- **[ddl-structural.md](ddl-structural.md)** — ADD/DROP CONSTRAINT, MODIFY PRIMARY KEY
- **[ddl-batching.md](ddl-batching.md)** — Batched migration pattern, error handling and recovery
