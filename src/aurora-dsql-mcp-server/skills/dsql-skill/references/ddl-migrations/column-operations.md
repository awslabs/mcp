# DDL Migrations: Column Operations

Step-by-step migration patterns for column-level changes using the Table Recreation Pattern.

**MUST read [overview.md](overview.md) first** for destructive operation warnings and the common verify & swap pattern.

---

## DROP COLUMN Migration

**Goal:** Remove a column from an existing table.

### Pre-Migration Validation

```sql
readonly_query("SELECT COUNT(*) as total_rows FROM target_table")
get_schema("target_table")
```

### Migration Steps

#### Step 1: Create new table excluding the column

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

#### Step 2: Migrate data

```sql
transact([
  "INSERT INTO target_table_new (id, tenant_id, kept_column1, kept_column2)
   SELECT id, tenant_id, kept_column1, kept_column2
   FROM target_table"
])
```

For tables > 3,000 rows, use [Batched Migration Pattern](batched-migration.md).

**Step 3: Verify and swap** (see [Common Pattern](overview.md#common-verify--swap-pattern))

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
