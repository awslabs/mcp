# DDL Migrations: Column Operations

Step-by-step migration patterns for column-level changes. `DROP COLUMN` runs as a direct statement; the remaining operations use the Table Recreation Pattern.

**MUST read [overview.md](overview.md) before any Table Recreation Pattern migration** for destructive operation warnings and the common verify & swap pattern.

---

## DROP COLUMN

**Goal:** Remove a column from an existing table.

DSQL supports `DROP COLUMN` directly. **MUST** issue the native statement rather than recreating the
table — the operation is synchronous and metadata-only, so it completes immediately and never drops
the table.

The dropped column's data becomes unreachable and no rollback exists once the transaction commits,
so **MUST** name the exact table and column to the user and obtain explicit confirmation first.

```sql
transact(["ALTER TABLE target_table DROP COLUMN obsolete_column"])
```

Dropping a non-key column that the primary key implicitly INCLUDEs is the ordinary case and needs no
special handling — DSQL rewrites the primary key definition automatically.

Several `DROP COLUMN` subcommands **MAY** share one `ALTER TABLE`. The
one-modification-per-statement rule in
[development-guide.md](../development-guide.md) applies to `ADD COLUMN` and `ALTER COLUMN`, not to
`DROP COLUMN`:

```sql
transact(["ALTER TABLE target_table DROP COLUMN obsolete_column, DROP COLUMN legacy_flag"])
```

### Rules

- **MUST** recreate the table instead when the column is a primary key *key* column. DSQL rejects
  that drop with `0A000 feature_not_supported`. See
  [MODIFY PRIMARY KEY](constraint-operations.md#modify-primary-key-migration) for that path.
- A bare drop already removes the column's indexes and its same-table constraints — `CHECK`,
  `DEFAULT`, `UNIQUE`, and a foreign key *defined on* the column. Issue the plain statement for
  these; adding `CASCADE` buys nothing and widens the blast radius.
- **MUST** add `CASCADE` only when something outside the table depends on the column — a view, or a
  foreign key in another table *referencing* it — or when a same-table `GENERATED ... STORED` column
  is computed from it. Without `CASCADE` those cases fail with
  `2BP01 dependent_objects_still_exist`. `CASCADE` drops the dependent objects too, so **MUST**
  present the dependency list to the user and obtain confirmation before using it:
  ```sql
  transact(["ALTER TABLE target_table DROP COLUMN obsolete_column CASCADE"])
  ```
- **MUST** fall back to table recreation when `CASCADE` itself fails with
  `0A000 feature_not_supported`. That means the dependency chain reaches a primary key key column —
  for example a PK column declared `GENERATED ALWAYS AS (obsolete_column) STORED`. DSQL refuses to
  cascade into the primary key, so no form of `DROP COLUMN` succeeds.
- **MAY** use `IF EXISTS` for idempotent migrations. Dropping an already-dropped column otherwise
  raises `42703 undefined_column`.

### Storage Impact

The drop hides the column rather than physically removing it, so table size does not fall right
away. Space returns as existing rows are updated. **MUST** tell the user that reclamation is
gradual.

### Column Budget

A table holds at most **255 active** columns and **1,600 over its lifetime**. Attribute numbers are
never reused, so each dropped column frees an active slot but still spends lifetime budget. A table
churned past 1,600 columns needs recreation — a later `ADD COLUMN` returns
`54011 too_many_columns`.

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

| From Type | To Type    | Validation                                              |
| --------- | ---------- | ------------------------------------------------------- |
| VARCHAR   | INTEGER    | MUST validate all values are numeric                    |
| VARCHAR   | BOOLEAN    | MUST validate values are 'true'/'false'/'t'/'f'/'1'/'0' |
| INTEGER   | VARCHAR    | Safe conversion                                         |
| TEXT      | VARCHAR(n) | MUST validate max length ≤ n                            |
| TIMESTAMP | DATE       | Safe (truncates time)                                   |
| INTEGER   | DECIMAL    | Safe conversion                                         |

### Migration Steps

#### Step 1: Create new table with changed type

```sql
transact([
  "CREATE TABLE target_table_new (
     id UUID PRIMARY KEY,
     converted_column INTEGER,  -- Changed from VARCHAR
     other_column TEXT
   )"
])
```

#### Step 2: Copy data with type casting

```sql
transact([
  "INSERT INTO target_table_new (id, converted_column, other_column)
   SELECT id, CAST(converted_column AS INTEGER), other_column
   FROM target_table"
])
```

For tables > 3,000 rows, use [Batched Migration Pattern](batched-migration.md).

**Step 3: Verify and swap** (see [Common Pattern](overview.md#common-verify--swap-pattern))

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

#### Step 1: Create new table with changed constraint

```sql
transact([
  "CREATE TABLE target_table_new (
     id UUID PRIMARY KEY,
     target_column VARCHAR(255) NOT NULL,  -- Changed from nullable
     other_column TEXT
   )"
])
```

#### Step 2: Copy data (with default for NULLs if needed)

```sql
transact([
  "INSERT INTO target_table_new (id, target_column, other_column)
   SELECT id, COALESCE(target_column, 'default_value'), other_column
   FROM target_table"
])
```

**Step 3: Verify and swap** (see [Common Pattern](overview.md#common-verify--swap-pattern))

---

## ALTER COLUMN SET/DROP DEFAULT Migration

**Goal:** Add or remove a default value for a column.

### Pre-Migration Validation

```sql
get_schema("target_table")
-- Identify current column definition and any existing defaults
```

### Migration Steps (SET DEFAULT)

#### Step 1: Create new table with default value

```sql
transact([
  "CREATE TABLE target_table_new (
     id UUID PRIMARY KEY,
     status VARCHAR(50) DEFAULT 'pending',  -- Added default
     other_column TEXT
   )"
])
```

#### Step 2: Copy data

```sql
transact([
  "INSERT INTO target_table_new (id, status, other_column)
   SELECT id, status, other_column
   FROM target_table"
])
```

**Step 3: Verify and swap** (see [Common Pattern](overview.md#common-verify--swap-pattern))

### Migration Steps (DROP DEFAULT)

#### Step 1: Create new table without default

```sql
transact([
  "CREATE TABLE target_table_new (
     id UUID PRIMARY KEY,
     status VARCHAR(50),  -- Removed DEFAULT
     other_column TEXT
   )"
])
```

#### Step 2: Copy data

```sql
transact([
  "INSERT INTO target_table_new (id, status, other_column)
   SELECT id, status, other_column
   FROM target_table"
])
```

**Step 3: Verify and swap** (see [Common Pattern](overview.md#common-verify--swap-pattern))
