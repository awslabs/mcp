# DDL Migrations: Constraint & Structural Operations

Step-by-step migration patterns for constraint changes, primary key modifications, and column transformations.

For table-recreation sections, **MUST** read
[overview.md](overview.md#table-recreation) first. The examples abbreviate unchanged schema; the
generated replacement **MUST** preserve every unchanged column, key, constraint, and default.

---

## ADD CHECK CONSTRAINT (Preferred)

**Goal:** Add a CHECK constraint to an existing table without table recreation.

This is the **preferred** approach for CHECK constraints. It avoids full table recreation by adding the constraint as NOT VALID (applies to new rows immediately) and then validating existing rows asynchronously in the background.

> **Note:** This pattern applies to CHECK constraints only. Add UNIQUE through a completed async
> unique index; PRIMARY KEY changes still require the Table Recreation Pattern.

### Migration Steps

#### Step 1: Add constraint with NOT VALID

```sql
transact([
  "ALTER TABLE target_table ADD CONSTRAINT chk_age CHECK (age >= 0) NOT VALID"
])
```

The constraint applies immediately to all new inserts and updates. Existing rows are not scanned.

#### Step 2: Validate asynchronously

```sql
transact([
  "ALTER TABLE ASYNC target_table VALIDATE CONSTRAINT chk_age"
])
-- Returns a job_id
```

#### Step 3: Monitor validation

**MUST** poll the returned `job_id` to a terminal state and inspect `details` on failure. Use the
terminal-state loop in [Foreign Key Constraints](../foreign-keys.md#dsql-specific-ddl).

`sys.wait_for_job` is a procedure, not a function. **MAY** call
`CALL sys.wait_for_job('<job_id>')` only through an autocommit database client outside the MCP
tools' explicit transactions.

### Outcomes

- **Success:** DSQL marks the constraint as VALID. The query planner enforces it for all queries.
- **Failure:** The constraint remains NOT VALID. Inspect `sys.jobs.details`; repair rows only when
  it identifies a constraint violation, then re-run `VALIDATE CONSTRAINT`.

---

## FOREIGN KEY CONSTRAINTS

Foreign keys do not use table recreation. Follow
[Foreign Key Constraints](../foreign-keys.md#dsql-specific-ddl) to add a constraint with `NOT VALID`,
validate it asynchronously, or drop it directly.

---

## ADD UNIQUE CONSTRAINT

**Goal:** Add a UNIQUE constraint to an existing table without table recreation.

### Pre-Migration Validation

**MUST validate existing data satisfies the new constraint.**

```sql
-- For UNIQUE constraint: check for duplicates
readonly_query(
  "SELECT target_column, COUNT(*) as cnt FROM target_table
   GROUP BY target_column HAVING COUNT(*) > 1 LIMIT 10"
)
-- MUST ABORT if any duplicates exist
```

### Migration Steps

1. Create the backing index and capture its `job_id`:

   ```python
   index_result = transact([
       "CREATE UNIQUE INDEX ASYNC users_email_unique_idx ON users (email)"
   ])
   ```

2. Poll `sys.jobs` to `completed` or `failed`, inspect `details` on failure, and verify
   `pg_index.indisvalid = true`.
3. Promote the valid index:

   ```python
   transact([
       "ALTER TABLE users ADD CONSTRAINT users_email_key "
       "UNIQUE USING INDEX users_email_unique_idx"
   ])
   ```

Aurora DSQL documents `ADD table_constraint_using_index` for this operation. The constraint takes
ownership of the index and may rename it to match the constraint.

---

## DROP CONSTRAINT

**Goal:** Remove a CHECK, UNIQUE, or foreign-key constraint without table recreation.

1. Confirm the named constraint and its type:

   ```python
   readonly_query(
       "SELECT conname, contype FROM pg_constraint "
       "WHERE conrelid = 'target_table'::regclass "
       "AND conname = 'target_constraint'"
   )
   ```

2. Explain the removed invariant and obtain confirmation.
3. Drop the named constraint directly:

   ```python
   transact(["ALTER TABLE target_table DROP CONSTRAINT target_constraint"])
   ```

Dropping a UNIQUE or PRIMARY KEY constraint also removes its owned index. Before dropping a
referenced UNIQUE constraint, verify that every retained foreign key still has a valid referenced
key or obtain approval to remove those relationships.

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

Review dependencies before starting
[Table Recreation](overview.md#table-recreation).
For every retained FK that references the current primary-key columns, the replacement **MUST**
keep those columns covered by a `PRIMARY KEY` or `UNIQUE` constraint. Obtain explicit approval
before removing a relationship; **MUST** abort when a retained FK cannot be restored.

### Migration Steps

#### Step 1: Create new table with new primary key

```sql
transact([
  "CREATE TABLE target_table_new (
     new_pk_column UUID PRIMARY KEY,  -- New PK
     old_pk_column VARCHAR(255) UNIQUE, -- Retain when inbound FKs reference the old key
     other_column TEXT
   )"
])
```

#### Step 2: Copy data

```sql
transact([
  "INSERT INTO target_table_new (new_pk_column, old_pk_column, other_column)
   SELECT new_pk_column, old_pk_column, other_column
   FROM target_table"
])
```

**Step 3: Verify and swap** (see [Common Pattern](overview.md#common-verify--swap-pattern))

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
