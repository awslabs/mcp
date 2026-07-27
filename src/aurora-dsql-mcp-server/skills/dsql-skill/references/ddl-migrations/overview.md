# DSQL DDL Migration Guide - Overview

This guide provides the **Table Recreation Pattern** for schema modifications that require rebuilding tables.

For column-level operations, see [column-operations.md](column-operations.md).
For constraint and structural operations, see [constraint-operations.md](constraint-operations.md).
For batched migration patterns, see [batched-migration.md](batched-migration.md).

---

## CRITICAL: Destructive Operations Warning

**The Table Recreation Pattern involves DESTRUCTIVE operations that can result in DATA LOSS.**

Table recreation requires dropping the original table, which is **irreversible**. If any step fails after the original table is dropped, data may be permanently lost.

### Mandatory User Verification Requirements

Agents MUST obtain explicit user approval before executing migrations on live tables:

1. **MUST present the complete migration plan** to the user before any execution
2. **MUST clearly state** that this operation will DROP the original table
3. **MUST confirm** the user has a current backup or accepts the risk of data loss
4. **MUST verify with the user** at each checkpoint before proceeding:
   - Before creating the new table structure
   - Before beginning data migration
   - Before dropping the original table (CRITICAL CHECKPOINT)
   - Before renaming the new table
5. **MUST NOT proceed** with any destructive action without explicit user confirmation
6. **MUST recommend** performing migrations on non-production environments first

### Risk Acknowledgment

Before proceeding, the user MUST confirm:

- [ ] They understand this is a destructive operation
- [ ] They have a backup of the table data (or accept the risk)
- [ ] They approve the agent to execute each step with verification
- [ ] They understand the migration cannot be automatically rolled back after DROP TABLE

---

## Table Recreation Operations

The following ALTER TABLE operations MUST use the **Table Recreation Pattern**:

| Operation                      | Key Approach                                   |
| ------------------------------ | ---------------------------------------------- |
| DROP COLUMN                    | Exclude column from new table                  |
| ALTER COLUMN TYPE              | Cast data type in SELECT                       |
| ALTER COLUMN SET/DROP NOT NULL | Change constraint in new table definition      |
| ALTER COLUMN SET/DROP DEFAULT  | Define default in new table definition         |
| ADD CONSTRAINT                 | Include constraint in new table definition     |
| DROP CONSTRAINT                | Remove constraint from new table definition    |
| MODIFY PRIMARY KEY             | Define new PK, validate uniqueness first       |
| Split/Merge Columns            | Use SPLIT_PART, SUBSTRING, or CONCAT in SELECT |

**Note:** The following operations ARE supported directly:

- `ALTER TABLE ... RENAME COLUMN` - Rename a column
- `ALTER TABLE ... RENAME TO` - Rename a table
- `ALTER TABLE ... ADD COLUMN` - Add a new column

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

Verify current limits via `awsknowledge`: `aurora dsql transaction limits`

- **MUST batch** migrations exceeding 3,000 row mutations
- **PREFER batches of 500-1,000 rows** for optimal throughput
- **MUST respect** 10 MiB data size per transaction
- **MUST respect** 5-minute transaction duration

---

## Common Verify & Swap Pattern

All migrations end with this pattern (referenced in [column-operations.md](column-operations.md) and [constraint-operations.md](constraint-operations.md)).

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

### Recovery — Row Counts Do Not Match

When `target_table_new` has fewer rows than `target_table`, treat the migration as incomplete.
The original table still holds the authoritative data, so recovery is always possible — **MUST NOT**
proceed with `DROP TABLE` until the counts agree.

1. **Diagnose** — find the missing rows by comparing ranges (for cursor-based migrations, query
   `target_table` for IDs greater than `MAX(id)` in `target_table_new`; for OFFSET-based, check
   which batch dropped rows by re-running the SELECT portion of each batch and comparing counts).
2. **Retry the missing batches** — insert the gap rows into `target_table_new` using the same
   batch pattern from [batched-migration.md](batched-migration.md). Because each `INSERT … SELECT`
   is idempotent on primary key, re-running completed batches is safe; they will collide on PK
   and error without writing duplicate data.
3. **If a type cast or constraint rejected rows** — migration cannot complete until the data is
   reconciled. Fix the source data in `target_table` (or adjust the new table's constraint),
   then re-run the missing batches.
4. **Escape hatch** — if diagnosis stalls, drop `target_table_new` and restart the migration
   from a clean slate. The original table is untouched, so no data is at risk.

Re-run the count comparison after each retry. Only proceed to `DROP TABLE` once
`COUNT(*)` matches exactly.

---

## Best Practices Summary

### User Verification (CRITICAL)

- **MUST present** complete migration plan to user before any execution
- **MUST obtain** explicit user confirmation before DROP TABLE operations
- **MUST verify** with user at each checkpoint during migration
- **MUST NOT** proceed with destructive actions without explicit user approval
- **MUST recommend** testing migrations on non-production data first
- **MUST confirm** user has backup or accepts data loss risk

### Technical Requirements

- **MUST validate** data compatibility before type changes
- **MUST batch** tables exceeding 3,000 rows
- **MUST verify** row counts before and after migration
- **MUST recreate** indexes after table swap using ASYNC
- **MUST NOT** drop original table until new table is verified
- **PREFER** cursor-based batching for very large tables
- **PREFER** batches of 500-1,000 rows for optimal throughput
