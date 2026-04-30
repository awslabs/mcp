# MySQL to DSQL: NULL and DEFAULT Constraints

Part of [MySQL to DSQL DDL Migration](ddl-operations.md). See [Common Verify & Swap Pattern](ddl-operations.md#common-verify--swap-pattern) for the shared migration end-pattern.

---

## ALTER COLUMN SET/DROP NOT NULL Migration

**MySQL syntax:**

```sql
ALTER TABLE table_name MODIFY COLUMN column_name datatype NOT NULL;
ALTER TABLE table_name MODIFY COLUMN column_name datatype NULL;
```

**DSQL:** MUST use **Table Recreation Pattern**.

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

**Step 3: Verify and swap** (see [Common Pattern](ddl-operations.md#common-verify--swap-pattern))

---

## ALTER COLUMN SET/DROP DEFAULT Migration

**MySQL syntax:**

```sql
ALTER TABLE table_name ALTER COLUMN column_name SET DEFAULT value;
ALTER TABLE table_name ALTER COLUMN column_name DROP DEFAULT;
```

**DSQL:** MUST use **Table Recreation Pattern**.

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

**Step 3: Verify and swap** (see [Common Pattern](ddl-operations.md#common-verify--swap-pattern))

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

**Step 3: Verify and swap** (see [Common Pattern](ddl-operations.md#common-verify--swap-pattern))
