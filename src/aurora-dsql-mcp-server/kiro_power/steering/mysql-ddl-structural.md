# MySQL to DSQL: Structural Changes

Part of [MySQL to DSQL DDL Migration](ddl-operations.md). For table recreation, read
[Table Recreation](../ddl-migrations/overview.md#table-recreation), then follow the
[Common Verify & Swap Pattern](ddl-operations.md#common-verify--swap-pattern).

---

## ADD/DROP CONSTRAINT Migration

**MySQL syntax:**

```sql
ALTER TABLE table_name ADD CONSTRAINT constraint_name UNIQUE (column_name);
ALTER TABLE table_name ADD CONSTRAINT constraint_name CHECK (condition);
ALTER TABLE table_name DROP CONSTRAINT constraint_name;
-- or MySQL-specific:
ALTER TABLE table_name DROP FOREIGN KEY foreign_key_name;
ALTER TABLE table_name DROP INDEX index_name;
ALTER TABLE table_name DROP CHECK constraint_name;
```

**DSQL direct mappings:**

- Add a foreign key with `NOT VALID`, validate it asynchronously, and translate MySQL
  `DROP FOREIGN KEY` to `DROP CONSTRAINT`. See [Foreign Key Constraints](../foreign-keys.md).
- Add a CHECK constraint with `NOT VALID`, then validate it asynchronously. See
  [Constraint Operations](../ddl-migrations/constraint-operations.md#add-check-constraint-preferred).
- Add a UNIQUE constraint through a completed `CREATE UNIQUE INDEX ASYNC`, then
  `ADD CONSTRAINT ... UNIQUE USING INDEX`. See
  [Constraint Operations](../ddl-migrations/constraint-operations.md#add-unique-constraint).
- Drop CHECK, UNIQUE, and foreign-key constraints directly with `DROP CONSTRAINT`. See
  [Constraint Operations](../ddl-migrations/constraint-operations.md#drop-constraint).
- Translate MySQL `ALTER TABLE table_name DROP INDEX index_name` to
  `DROP INDEX index_name`.

### Pre-Migration Validation (for ADD CONSTRAINT)

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

---

## MODIFY PRIMARY KEY Migration

**MySQL syntax:**

```sql
ALTER TABLE table_name DROP PRIMARY KEY, ADD PRIMARY KEY (new_column);
```

**DSQL:** MUST use **Table Recreation Pattern**.

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
[Table Recreation](../ddl-migrations/overview.md#table-recreation).
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

**Step 3: Verify and swap** (see [Common Pattern](ddl-operations.md#common-verify--swap-pattern))
