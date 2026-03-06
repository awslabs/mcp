# DSQL DDL Migration Guide

This guide provides the **Table Recreation Pattern** for schema modifications that require rebuilding tables.

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

| Operation | Key Approach |
|-----------|--------------|
| DROP COLUMN | Exclude column from new table |
| ALTER COLUMN TYPE | Cast data type in SELECT |
| ALTER COLUMN SET/DROP NOT NULL | Change constraint in new table definition |
| ALTER COLUMN SET/DROP DEFAULT | Define default in new table definition |
| ADD CONSTRAINT | Include constraint in new table definition |
| DROP CONSTRAINT | Remove constraint from new table definition |
| MODIFY PRIMARY KEY | Define new PK, validate uniqueness first |
| Split/Merge Columns | Use SPLIT_PART, SUBSTRING, or CONCAT in SELECT |

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

## DROP COLUMN Migration

**Goal:** Remove a column from an existing table.

### Pre-Migration Validation

```sql
readonly_query("SELECT COUNT(*) as total_rows FROM target_table")
get_schema("target_table")
```

### Migration Steps

**Step 1: Create new table excluding the column**
```sql
transact([
  "CREATE TABLE target_table_new (
     id UUID PRIMARY KEY,
     tenant_id VARCHAR(255) NOT NULL,
     kept_column1 VARCHAR(255),
     kept_column2 INTEGER
     -- dropped_column is NOT included
   )"
])
```

**Step 2: Migrate data**
```sql
transact([
  "INSERT INTO target_table_new (id, tenant_id, kept_column1, kept_column2)
   SELECT id, tenant_id, kept_column1, kept_column2
   FROM target_table"
])
```
For tables > 3,000 rows, use [Batched Migration Pattern](#batched-migration-pattern).

**Step 3: Verify and swap** (see [Common Pattern](#common-verify--swap-pattern))

---

## ALTER COLUMN TYPE Migration

**Goal:** Change a column's data type.

### Pre-Migration Validation

**MUST validate data compatibility BEFORE migration** to prevent data loss.

```sql
-- Example: VARCHAR to INTEGER - check for non-numeric values
readonly_query(
  "SELECT COUNT(*) as invalid_count FROM target_table
   WHERE column_to_change !~ '^-?[0-9]+$'"
)
-- MUST abort if invalid_count > 0

-- Show problematic rows
readonly_query(
  "SELECT id, column_to_change FROM target_table
   WHERE column_to_change !~ '^-?[0-9]+$' LIMIT 100"
)
```

### Data Type Compatibility Matrix

| From Type | To Type | Validation |
|-----------|---------|------------|
| VARCHAR → INTEGER | MUST validate all values are numeric |
| VARCHAR → BOOLEAN | MUST validate values are 'true'/'false'/'t'/'f'/'1'/'0' |
| INTEGER → VARCHAR | Safe conversion |
| TEXT → VARCHAR(n) | MUST validate max length ≤ n |
| TIMESTAMP → DATE | Safe (truncates time) |
| INTEGER → DECIMAL | Safe conversion |

### Migration Steps

**Step 1: Create new table with changed type**
```sql
transact([
  "CREATE TABLE target_table_new (
     id UUID PRIMARY KEY,
     converted_column INTEGER,  -- Changed from VARCHAR
     other_column TEXT
   )"
])
```

**Step 2: Copy data with type casting**
```sql
transact([
  "INSERT INTO target_table_new (id, converted_column, other_column)
   SELECT id, CAST(converted_column AS INTEGER), other_column
   FROM target_table"
])
```

**Step 3: Verify and swap** (see [Common Pattern](#common-verify--swap-pattern))

---

## ALTER COLUMN SET/DROP NOT NULL Migration

**Goal:** Change a column's nullability constraint.

### Pre-Migration Validation (for SET NOT NULL)

```sql
readonly_query(
  "SELECT COUNT(*) as null_count FROM target_table
   WHERE target_column IS NULL"
)
-- MUST ABORT if null_count > 0, or plan to provide default values
```

### Migration Steps

**Step 1: Create new table with changed constraint**
```sql
transact([
  "CREATE TABLE target_table_new (
     id UUID PRIMARY KEY,
     target_column VARCHAR(255) NOT NULL,  -- Changed from nullable
     other_column TEXT
   )"
])
```

**Step 2: Copy data (with default for NULLs if needed)**
```sql
transact([
  "INSERT INTO target_table_new (id, target_column, other_column)
   SELECT id, COALESCE(target_column, 'default_value'), other_column
   FROM target_table"
])
```

**Step 3: Verify and swap** (see [Common Pattern](#common-verify--swap-pattern))

---

## ALTER COLUMN SET/DROP DEFAULT Migration

**Goal:** Add or remove a default value for a column.

### Pre-Migration Validation

```sql
get_schema("target_table")
-- Identify current column definition and any existing defaults
```

### Migration Steps (SET DEFAULT)

**Step 1: Create new table with default value**
```sql
transact([
  "CREATE TABLE target_table_new (
     id UUID PRIMARY KEY,
     status VARCHAR(50) DEFAULT 'pending',  -- Added default
     other_column TEXT
   )"
])
```

**Step 2: Copy data**
```sql
transact([
  "INSERT INTO target_table_new (id, status, other_column)
   SELECT id, status, other_column
   FROM target_table"
])
```

**Step 3: Verify and swap** (see [Common Pattern](#common-verify--swap-pattern))

### Migration Steps (DROP DEFAULT)

**Step 1: Create new table without default**
```sql
transact([
  "CREATE TABLE target_table_new (
     id UUID PRIMARY KEY,
     status VARCHAR(50),  -- Removed DEFAULT
     other_column TEXT
   )"
])
```

**Step 2: Copy data**
```sql
transact([
  "INSERT INTO target_table_new (id, status, other_column)
   SELECT id, status, other_column
   FROM target_table"
])
```

**Step 3: Verify and swap** (see [Common Pattern](#common-verify--swap-pattern))

---

## ADD CONSTRAINT Migration

**Goal:** Add a constraint (UNIQUE, CHECK) to an existing table.

### Pre-Migration Validation

**MUST validate existing data satisfies the new constraint.**

```sql
-- For UNIQUE constraint: check for duplicates
readonly_query(
  "SELECT target_column, COUNT(*) as cnt FROM target_table
   GROUP BY target_column HAVING COUNT(*) > 1 LIMIT 10"
)
-- MUST ABORT if any duplicates exist

-- For CHECK constraint: validate all rows pass
readonly_query(
  "SELECT COUNT(*) as invalid_count FROM target_table
   WHERE NOT (check_condition)"
)
-- MUST ABORT if invalid_count > 0
```

### Migration Steps

**Step 1: Create new table with the constraint**
```sql
transact([
  "CREATE TABLE target_table_new (
     id UUID PRIMARY KEY,
     email VARCHAR(255) UNIQUE,  -- Added UNIQUE constraint
     age INTEGER CHECK (age >= 0),  -- Added CHECK constraint
     other_column TEXT
   )"
])
```

**Step 2: Copy data**
```sql
transact([
  "INSERT INTO target_table_new (id, email, age, other_column)
   SELECT id, email, age, other_column
   FROM target_table"
])
```

**Step 3: Verify and swap** (see [Common Pattern](#common-verify--swap-pattern))

---

## DROP CONSTRAINT Migration

**Goal:** Remove a constraint (UNIQUE, CHECK) from a table.

### Pre-Migration Validation

```sql
-- Identify existing constraints
readonly_query(
  "SELECT constraint_name, constraint_type
   FROM information_schema.table_constraints
   WHERE table_name = 'target_table'
   AND constraint_type IN ('UNIQUE', 'CHECK')"
)
```

### Migration Steps

**Step 1: Create new table without the constraint**
```sql
transact([
  "CREATE TABLE target_table_new (
     id UUID PRIMARY KEY,
     email VARCHAR(255),  -- Removed UNIQUE constraint
     other_column TEXT
   )"
])
```

**Step 2: Copy data**
```sql
transact([
  "INSERT INTO target_table_new (id, email, other_column)
   SELECT id, email, other_column
   FROM target_table"
])
```

**Step 3: Verify and swap** (see [Common Pattern](#common-verify--swap-pattern))

---

## MODIFY PRIMARY KEY Migration

**Goal:** Change which column(s) form the primary key.

### Pre-Migration Validation

**MUST validate new PK column has unique, non-null values.**

```sql
-- Check for duplicates
readonly_query(
  "SELECT new_pk_column, COUNT(*) as cnt FROM target_table
   GROUP BY new_pk_column HAVING COUNT(*) > 1 LIMIT 10"
)
-- MUST ABORT if any duplicates exist

-- Check for NULLs
readonly_query(
  "SELECT COUNT(*) as null_count FROM target_table
   WHERE new_pk_column IS NULL"
)
-- MUST ABORT if null_count > 0
```

### Migration Steps

**Step 1: Create new table with new primary key**
```sql
transact([
  "CREATE TABLE target_table_new (
     new_pk_column UUID PRIMARY KEY,  -- New PK
     old_pk_column VARCHAR(255),      -- Demoted to regular column
     other_column TEXT
   )"
])
```

**Step 2: Copy data**
```sql
transact([
  "INSERT INTO target_table_new (new_pk_column, old_pk_column, other_column)
   SELECT new_pk_column, old_pk_column, other_column
   FROM target_table"
])
```

**Step 3: Verify and swap** (see [Common Pattern](#common-verify--swap-pattern))

---

## Column Transformations (Split/Merge)

### Split Column

**Goal:** Split one column into multiple (e.g., `full_name` → `first_name` + `last_name`).

```sql
-- Create new table with split columns
transact([
  "CREATE TABLE target_table_new (
     id UUID PRIMARY KEY,
     first_name VARCHAR(255),
     last_name VARCHAR(255)
   )"
])

-- Copy with transformation
transact([
  "INSERT INTO target_table_new (id, first_name, last_name)
   SELECT id,
     SPLIT_PART(full_name, ' ', 1),
     SUBSTRING(full_name FROM POSITION(' ' IN full_name) + 1)
   FROM target_table"
])

-- Verify, swap, re-index (see Common Pattern)
```

### Merge Columns

**Goal:** Combine multiple columns into one (e.g., `first_name` + `last_name` → `display_name`).

```sql
-- Create new table with merged column
transact([
  "CREATE TABLE target_table_new (
     id UUID PRIMARY KEY,
     display_name VARCHAR(512)
   )"
])

-- Copy with concatenation
transact([
  "INSERT INTO target_table_new (id, display_name)
   SELECT id,
     CONCAT(COALESCE(first_name, ''), ' ', COALESCE(last_name, ''))
   FROM target_table"
])

-- Verify, swap, re-index (see Common Pattern)
```

---

## Batched Migration Pattern

**REQUIRED for tables exceeding 3,000 rows.**

### Batch Size Rules

- **PREFER batches of 500-1,000 rows** for optimal performance
- Smaller batches reduce lock contention and enable better concurrency

### OFFSET-Based Batching

```sql
readonly_query("SELECT COUNT(*) as total FROM target_table")
-- Calculate: batches_needed = CEIL(total / 1000)

-- Batch 1
transact([
  "INSERT INTO target_table_new (id, col1, col2)
   SELECT id, col1, col2 FROM target_table
   ORDER BY id LIMIT 1000 OFFSET 0"
])

-- Batch 2
transact([
  "INSERT INTO target_table_new (id, col1, col2)
   SELECT id, col1, col2 FROM target_table
   ORDER BY id LIMIT 1000 OFFSET 1000"
])
-- Continue until all rows migrated...
```

### Cursor-Based Batching (Preferred for Large Tables)

Better performance than OFFSET for very large tables:

```sql
-- First batch
transact([
  "INSERT INTO target_table_new (id, col1, col2)
   SELECT id, col1, col2 FROM target_table
   ORDER BY id LIMIT 1000"
])

-- Get last processed ID
readonly_query("SELECT MAX(id) as last_id FROM target_table_new")

-- Subsequent batches
transact([
  "INSERT INTO target_table_new (id, col1, col2)
   SELECT id, col1, col2 FROM target_table
   WHERE id > 'last_processed_id'
   ORDER BY id LIMIT 1000"
])
```

### Progress Tracking

```sql
readonly_query(
  "SELECT (SELECT COUNT(*) FROM target_table_new) as migrated,
          (SELECT COUNT(*) FROM target_table) as total"
)
```

---

## Error Handling

### Pre-Migration Checks

1. **Verify table exists**
   ```sql
   readonly_query(
     "SELECT table_name FROM information_schema.tables
      WHERE table_name = 'target_table'"
   )
   ```

2. **Verify DDL permissions**

### Data Validation Errors

**MUST abort migration and report** when:
- Type conversion would fail
- Value truncation would occur
- NOT NULL constraint would be violated

```sql
-- Find problematic rows
readonly_query(
  "SELECT id, problematic_column FROM target_table
   WHERE problematic_column !~ '^-?[0-9]+$' LIMIT 100"
)
```

### Recovery from Failed Migration

```sql
-- Check table state
readonly_query(
  "SELECT table_name FROM information_schema.tables
   WHERE table_name IN ('target_table', 'target_table_new')"
)
```

- **Both tables exist:** Original safe → `DROP TABLE IF EXISTS target_table_new` and restart
- **Only new table exists:** Verify count, then complete rename

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
