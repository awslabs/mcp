# DDL Migrations: Constraint & Structural Operations

Step-by-step migration patterns for constraint changes, primary key modifications, and column transformations.

**MUST read [overview.md](overview.md) first** for destructive operation warnings and the common verify & swap pattern.

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

#### Step 1: Create new table with the constraint

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

#### Step 2: Copy data

```sql
transact([
  "INSERT INTO target_table_new (id, email, age, other_column)
   SELECT id, email, age, other_column
   FROM target_table"
])
```

**Step 3: Verify and swap** (see [Common Pattern](overview.md#common-verify--swap-pattern))

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

#### Step 1: Create new table without the constraint

```sql
transact([
  "CREATE TABLE target_table_new (
     id UUID PRIMARY KEY,
     email VARCHAR(255),  -- Removed UNIQUE constraint
     other_column TEXT
   )"
])
```

#### Step 2: Copy data

```sql
transact([
  "INSERT INTO target_table_new (id, email, other_column)
   SELECT id, email, other_column
   FROM target_table"
])
```

**Step 3: Verify and swap** (see [Common Pattern](overview.md#common-verify--swap-pattern))

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

#### Step 1: Create new table with new primary key

```sql
transact([
  "CREATE TABLE target_table_new (
     new_pk_column UUID PRIMARY KEY,  -- New PK
     old_pk_column VARCHAR(255),      -- Demoted to regular column
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
