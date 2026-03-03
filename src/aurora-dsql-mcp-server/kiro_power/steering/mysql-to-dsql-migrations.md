# MySQL to DSQL Migration Guide

This guide provides migration patterns for converting MySQL DDL operations to Aurora DSQL-compatible equivalents, including the **Table Recreation Pattern** for schema modifications that require rebuilding tables.

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

## MySQL Data Type Mapping to DSQL

Map MySQL data types to their DSQL equivalents.

### Numeric Types

| MySQL Type | DSQL Equivalent | Notes |
|------------|----------------|-------|
| TINYINT | SMALLINT | DSQL has no TINYINT; SMALLINT is smallest integer type |
| SMALLINT | SMALLINT | Direct equivalent |
| MEDIUMINT | INTEGER | DSQL has no MEDIUMINT; use INTEGER |
| INT / INTEGER | INTEGER | Direct equivalent |
| BIGINT | BIGINT | Direct equivalent |
| TINYINT(1) | BOOLEAN | MySQL convention for booleans maps to native BOOLEAN |
| FLOAT | REAL | Direct equivalent |
| DOUBLE | DOUBLE PRECISION | Direct equivalent |
| DECIMAL(p,s) / NUMERIC(p,s) | DECIMAL(p,s) / NUMERIC(p,s) | Direct equivalent |
| BIT(1) | BOOLEAN | Single bit maps to BOOLEAN |
| BIT(n) | BYTEA | Multi-bit maps to BYTEA |
| UNSIGNED integers | Use next-larger signed type or CHECK constraint | DSQL has no UNSIGNED; use CHECK (col >= 0) |

### String Types

| MySQL Type | DSQL Equivalent | Notes |
|------------|----------------|-------|
| CHAR(n) | CHAR(n) | Direct equivalent |
| VARCHAR(n) | VARCHAR(n) | Direct equivalent |
| TINYTEXT | TEXT | DSQL uses TEXT for all unbounded strings |
| TEXT | TEXT | Direct equivalent |
| MEDIUMTEXT | TEXT | DSQL uses TEXT for all unbounded strings |
| LONGTEXT | TEXT | DSQL uses TEXT for all unbounded strings |
| ENUM('a','b','c') | VARCHAR(255) with CHECK constraint | See [ENUM Migration](#enum-type-migration) |
| SET('a','b','c') | TEXT | Store as comma-separated TEXT; see [SET Migration](#set-type-migration) |

### Date/Time Types

| MySQL Type | DSQL Equivalent | Notes |
|------------|----------------|-------|
| DATE | DATE | Direct equivalent |
| DATETIME | TIMESTAMP | DATETIME maps to TIMESTAMP |
| TIMESTAMP | TIMESTAMP | Direct equivalent; MUST manage auto-updates in application layer |
| TIME | TIME | Direct equivalent |
| YEAR | INTEGER | Store as 4-digit integer |

### Binary Types

| MySQL Type | DSQL Equivalent | Notes |
|------------|----------------|-------|
| BINARY(n) | BYTEA | DSQL uses BYTEA for binary data |
| VARBINARY(n) | BYTEA | DSQL uses BYTEA for binary data |
| TINYBLOB | BYTEA | DSQL uses BYTEA for all binary data |
| BLOB | BYTEA | DSQL uses BYTEA for all binary data |
| MEDIUMBLOB | BYTEA | DSQL uses BYTEA for all binary data |
| LONGBLOB | BYTEA | DSQL uses BYTEA for all binary data |

### Other Types

| MySQL Type | DSQL Equivalent | Notes |
|------------|----------------|-------|
| JSON | TEXT | MUST store as TEXT |
| AUTO_INCREMENT | UUID with gen_random_uuid(), IDENTITY column, or SEQUENCE | See [AUTO_INCREMENT Migration](#auto_increment-migration) for all three options |

---

## MySQL Features Requiring DSQL Alternatives

MUST use the following DSQL alternatives for these MySQL features:

| MySQL Feature | DSQL Alternative |
|--------------|-----------------|
| FOREIGN KEY constraints | Application-layer referential integrity |
| FULLTEXT indexes | Application-layer text search |
| SPATIAL indexes | Application-layer spatial queries |
| ENGINE=InnoDB/MyISAM | MUST omit (DSQL manages storage automatically) |
| ON UPDATE CURRENT_TIMESTAMP | Application-layer timestamp management |
| GENERATED columns (virtual/stored) | Application-layer computation |
| PARTITION BY | MUST omit (DSQL manages distribution automatically) |
| TRIGGERS | Application-layer logic |
| STORED PROCEDURES / FUNCTIONS | Application-layer logic |

---

## MySQL DDL Operation Mapping

### Directly Supported Operations

These MySQL operations have direct DSQL equivalents:

| MySQL DDL | DSQL Equivalent |
|-----------|----------------|
| `CREATE TABLE ...` | `CREATE TABLE ...` (with type adjustments) |
| `DROP TABLE table_name` | `DROP TABLE table_name` |
| `ALTER TABLE ... ADD COLUMN col type` | `ALTER TABLE ... ADD COLUMN col type` |
| `ALTER TABLE ... RENAME COLUMN old TO new` | `ALTER TABLE ... RENAME COLUMN old TO new` |
| `ALTER TABLE ... RENAME TO new_name` | `ALTER TABLE ... RENAME TO new_name` |
| `CREATE INDEX idx ON t(col)` | `CREATE INDEX ASYNC idx ON t(col)` (MUST use ASYNC) |
| `DROP INDEX idx ON t` | `DROP INDEX idx` (MUST omit the ON clause) |

### Operations Requiring Table Recreation Pattern

These MySQL operations MUST use the **Table Recreation Pattern** in DSQL:

| MySQL DDL | DSQL Approach |
|-----------|--------------|
| `ALTER TABLE ... MODIFY COLUMN col new_type` | Table recreation with type cast |
| `ALTER TABLE ... CHANGE COLUMN old new new_type` | Table recreation (type change) or RENAME COLUMN (rename only) |
| `ALTER TABLE ... ALTER COLUMN col datatype` | Table recreation with type cast |
| `ALTER TABLE ... DROP COLUMN col` | Table recreation excluding the column |
| `ALTER TABLE ... ALTER COLUMN col SET DEFAULT val` | Table recreation with DEFAULT in new definition |
| `ALTER TABLE ... ALTER COLUMN col DROP DEFAULT` | Table recreation without DEFAULT |
| `ALTER TABLE ... ADD CONSTRAINT ... UNIQUE` | Table recreation with constraint |
| `ALTER TABLE ... ADD CONSTRAINT ... CHECK` | Table recreation with constraint |
| `ALTER TABLE ... DROP CONSTRAINT ...` | Table recreation without constraint |
| `ALTER TABLE ... DROP PRIMARY KEY, ADD PRIMARY KEY (new_cols)` | Table recreation with new PK |

### Operations Requiring Application-Layer Implementation

MUST implement these MySQL operations at the application layer:

| MySQL DDL | DSQL Approach |
|-----------|--------------|
| `ALTER TABLE ... ADD FOREIGN KEY` | MUST implement referential integrity in application layer |
| `ALTER TABLE ... ADD FULLTEXT INDEX` | MUST implement text search in application layer |
| `ALTER TABLE ... ADD SPATIAL INDEX` | MUST implement spatial queries in application layer |
| `ALTER TABLE ... ENGINE=...` | MUST omit |
| `ALTER TABLE ... AUTO_INCREMENT=...` | Use SEQUENCE with setval() or IDENTITY column |
| `CREATE TRIGGER` | MUST implement in application-layer logic |
| `CREATE PROCEDURE` / `CREATE FUNCTION` | MUST implement in application-layer logic |

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

## ALTER TABLE ... ALTER COLUMN (Change Column Type)

**MySQL syntax:**
```sql
ALTER TABLE table_name ALTER COLUMN column_name datatype;
-- or MySQL-specific:
ALTER TABLE table_name MODIFY COLUMN column_name new_datatype;
ALTER TABLE table_name CHANGE COLUMN old_name new_name new_datatype;
```

**DSQL:** MUST use **Table Recreation Pattern**.

### Pre-Migration Validation

**MUST validate data compatibility BEFORE migration** to prevent data loss.

```sql
-- Get current table state
readonly_query("SELECT COUNT(*) as total_rows FROM target_table")
get_schema("target_table")

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

### MySQL-to-DSQL Type Conversion Validation Matrix

| MySQL From Type | DSQL To Type | Validation |
|----------------|-------------|------------|
| VARCHAR → INT/INTEGER | VARCHAR → INTEGER | MUST validate all values are numeric |
| VARCHAR → TINYINT(1)/BOOLEAN | VARCHAR → BOOLEAN | MUST validate values are 'true'/'false'/'t'/'f'/'1'/'0' |
| INT/INTEGER → VARCHAR | INTEGER → VARCHAR | Safe conversion |
| TEXT → VARCHAR(n) | TEXT → VARCHAR(n) | MUST validate max length ≤ n |
| DATETIME → DATE | TIMESTAMP → DATE | Safe (truncates time) |
| INT → DECIMAL | INTEGER → DECIMAL | Safe conversion |
| ENUM → VARCHAR | VARCHAR → VARCHAR | Safe (already stored as VARCHAR in DSQL) |
| MEDIUMINT → BIGINT | INTEGER → BIGINT | Safe conversion |
| FLOAT → DECIMAL | REAL → DECIMAL | May lose precision; MUST validate acceptable |

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

## ALTER TABLE ... DROP COLUMN

**MySQL syntax:**
```sql
ALTER TABLE table_name DROP COLUMN column_name;
```

**DSQL:** MUST use **Table Recreation Pattern**.

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

## AUTO_INCREMENT Migration

**MySQL syntax:**
```sql
CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255)
);
```

DSQL provides three options for replacing MySQL's AUTO_INCREMENT. Choose based on your workload requirements. See [Choosing Identifier Types](development-guide.md#choosing-identifier-types) in the development guide for detailed guidance.

**ALWAYS use `GENERATED AS IDENTITY`** for auto-incrementing integer columns.

### Option 1: UUID Primary Key (Recommended for Scalability)

UUIDs are the recommended default because they avoid coordination and scale well for distributed writes.

```sql
transact([
  "CREATE TABLE users (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     name VARCHAR(255)
   )"
])
```

### Option 2: IDENTITY Column (Recommended for Integer Auto-Increment)

Use `GENERATED { ALWAYS | BY DEFAULT } AS IDENTITY` when compact, human-readable integer IDs are needed. CACHE **MUST** be specified explicitly as either `1` or `>= 65536`.

```sql
-- GENERATED ALWAYS: DSQL always generates the value; explicit inserts rejected unless OVERRIDING SYSTEM VALUE
transact([
  "CREATE TABLE users (
     id BIGINT GENERATED ALWAYS AS IDENTITY (CACHE 65536) PRIMARY KEY,
     name VARCHAR(255)
   )"
])

-- GENERATED BY DEFAULT: DSQL generates a value unless an explicit value is provided (closer to MySQL AUTO_INCREMENT behavior)
transact([
  "CREATE TABLE users (
     id BIGINT GENERATED BY DEFAULT AS IDENTITY (CACHE 65536) PRIMARY KEY,
     name VARCHAR(255)
   )"
])
```

#### Choosing a CACHE Size

**REQUIRED:** Specify CACHE explicitly. Supported values are `1` or `>= 65536`.

- **CACHE >= 65536** — High-frequency inserts, many concurrent sessions, tolerates gaps and ordering effects (e.g., IoT/telemetry, job IDs, order numbers)
- **CACHE = 1** — Low allocation rates, identifiers should follow allocation order closely, minimizing gaps matters more than throughput (e.g., account numbers, reference numbers)

### Option 3: Explicit SEQUENCE

Use a standalone sequence when multiple tables share a counter or when you need `nextval`/`setval` control.

```sql
-- Create the sequence (CACHE MUST be 1 or >= 65536)
transact(["CREATE SEQUENCE users_id_seq CACHE 65536 START 1"])

-- Create table using the sequence
transact([
  "CREATE TABLE users (
     id BIGINT PRIMARY KEY DEFAULT nextval('users_id_seq'),
     name VARCHAR(255)
   )"
])
```

### Migrating Existing AUTO_INCREMENT Data

#### To UUID Primary Key

```sql
transact([
  "CREATE TABLE users_new (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     legacy_id INTEGER,  -- Preserve original AUTO_INCREMENT ID for reference
     name VARCHAR(255)
   )"
])

transact([
  "INSERT INTO users_new (id, legacy_id, name)
   SELECT gen_random_uuid(), id, name
   FROM users"
])
```

If other tables reference the old integer ID, update those references to use the new UUID or the `legacy_id` column.

#### To IDENTITY Column (Preserving Integer IDs)

```sql
-- Use GENERATED BY DEFAULT to allow explicit ID values during migration
transact([
  "CREATE TABLE users_new (
     id BIGINT GENERATED BY DEFAULT AS IDENTITY (CACHE 65536) PRIMARY KEY,
     name VARCHAR(255)
   )"
])

-- Migrate with original integer IDs preserved
transact([
  "INSERT INTO users_new (id, name)
   SELECT id, name
   FROM users"
])

-- Set the identity sequence to continue after the max existing ID
-- Get the max ID first:
readonly_query("SELECT MAX(id) as max_id FROM users_new")
-- Then reset the sequence (replace 'users_new_id_seq' with actual sequence name from get_schema):
transact(["SELECT setval('users_new_id_seq', (SELECT MAX(id) FROM users_new))"])
```

**Verify and swap** (see [Common Pattern](#common-verify--swap-pattern))

---

## ENUM Type Migration

**MySQL syntax:**
```sql
CREATE TABLE orders (
  id INT AUTO_INCREMENT PRIMARY KEY,
  status ENUM('pending', 'processing', 'shipped', 'delivered') NOT NULL
);
```

**DSQL equivalent using VARCHAR with CHECK:**
```sql
transact([
  "CREATE TABLE orders (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     status VARCHAR(255) NOT NULL CHECK (status IN ('pending', 'processing', 'shipped', 'delivered'))
   )"
])
```

### Migrating Existing ENUM Data

```sql
-- ENUM values are already stored as strings; direct copy is safe
transact([
  "INSERT INTO orders_new (id, status)
   SELECT gen_random_uuid(), status
   FROM orders"
])
```

---

## SET Type Migration

**MySQL syntax:**
```sql
CREATE TABLE user_preferences (
  id INT AUTO_INCREMENT PRIMARY KEY,
  permissions SET('read', 'write', 'delete', 'admin')
);
```

**DSQL equivalent using TEXT (comma-separated):**
```sql
transact([
  "CREATE TABLE user_preferences (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     permissions TEXT  -- Stored as comma-separated: 'read,write,admin'
   )"
])
```

**Note:** Application layer MUST validate and parse SET values. MySQL stores SET values as comma-separated strings internally, so direct migration preserves the format.

---

## ON UPDATE CURRENT_TIMESTAMP Migration

**MySQL syntax:**
```sql
CREATE TABLE records (
  id INT AUTO_INCREMENT PRIMARY KEY,
  data TEXT,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

**DSQL equivalent:**
```sql
transact([
  "CREATE TABLE records (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     data TEXT,
     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   )"
])
```

**MUST explicitly set** `updated_at = CURRENT_TIMESTAMP` in every UPDATE statement to replicate `ON UPDATE CURRENT_TIMESTAMP` behavior:

```sql
transact([
  "UPDATE records SET data = 'new_value', updated_at = CURRENT_TIMESTAMP
   WHERE id = 'record-uuid'"
])
```

---

## FOREIGN KEY Migration

**MySQL syntax:**
```sql
CREATE TABLE orders (
  id INT AUTO_INCREMENT PRIMARY KEY,
  customer_id INT,
  FOREIGN KEY (customer_id) REFERENCES customers(id)
);
```

**MUST implement referential integrity at the application layer:**
```sql
-- Create table with reference column (enforce integrity in application layer)
transact([
  "CREATE TABLE orders (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     customer_id UUID NOT NULL
   )"
])

-- Create index for the reference column
transact(["CREATE INDEX ASYNC idx_orders_customer ON orders(customer_id)"])
```

**Application layer MUST enforce referential integrity:**
```sql
-- Before INSERT: validate parent exists
readonly_query(
  "SELECT id FROM customers WHERE id = 'customer-uuid'"
)
-- MUST abort INSERT if parent not found

-- Before DELETE of parent: check for dependents
readonly_query(
  "SELECT COUNT(*) as dependent_count FROM orders
   WHERE customer_id = 'customer-uuid'"
)
-- MUST abort DELETE if dependent_count > 0
```

---

## Full MySQL CREATE TABLE Migration Example

### Original MySQL Schema

```sql
CREATE TABLE products (
  id INT AUTO_INCREMENT PRIMARY KEY,
  tenant_id INT NOT NULL,
  name VARCHAR(255) NOT NULL,
  description MEDIUMTEXT,
  price DECIMAL(10,2) NOT NULL,
  category ENUM('electronics', 'clothing', 'food', 'other') DEFAULT 'other',
  tags SET('sale', 'new', 'featured'),
  metadata JSON,
  stock INT UNSIGNED DEFAULT 0,
  is_active TINYINT(1) DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  INDEX idx_tenant (tenant_id),
  INDEX idx_category (category),
  FULLTEXT INDEX idx_name_desc (name, description)
) ENGINE=InnoDB;
```

### Migrated DSQL Schema

```sql
-- Step 1: Create table (one DDL per transaction)
transact([
  "CREATE TABLE products (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     tenant_id VARCHAR(255) NOT NULL,
     name VARCHAR(255) NOT NULL,
     description TEXT,
     price DECIMAL(10,2) NOT NULL,
     category VARCHAR(255) DEFAULT 'other' CHECK (category IN ('electronics', 'clothing', 'food', 'other')),
     tags TEXT,
     metadata TEXT,
     stock INTEGER DEFAULT 0 CHECK (stock >= 0),
     is_active BOOLEAN DEFAULT true,
     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   )"
])

-- Step 2: Create indexes (each in separate transaction, MUST use ASYNC)
transact(["CREATE INDEX ASYNC idx_products_tenant ON products(tenant_id)"])
transact(["CREATE INDEX ASYNC idx_products_category ON products(tenant_id, category)"])
-- MUST implement text search at application layer for FULLTEXT index equivalent
```

### Migration Decisions Summary

| MySQL Feature | DSQL Decision |
|--------------|--------------|
| `AUTO_INCREMENT` | UUID with `gen_random_uuid()`, or IDENTITY column with CACHE, or SEQUENCE (see [AUTO_INCREMENT Migration](#auto_increment-migration)) |
| `INT` tenant_id | `VARCHAR(255)` for multi-tenant pattern |
| `MEDIUMTEXT` | `TEXT` |
| `ENUM(...)` | `VARCHAR(255)` with `CHECK` constraint |
| `SET(...)` | `TEXT` (comma-separated) |
| `JSON` | `TEXT` (JSON.stringify) |
| `UNSIGNED` | `CHECK (col >= 0)` |
| `TINYINT(1)` | `BOOLEAN` |
| `DATETIME` | `TIMESTAMP` |
| `ON UPDATE CURRENT_TIMESTAMP` | Application-layer `SET updated_at = CURRENT_TIMESTAMP` |
| `FOREIGN KEY` | Application-layer referential integrity |
| `INDEX` | `CREATE INDEX ASYNC` |
| `FULLTEXT INDEX` | Application-layer text search |
| `ENGINE=InnoDB` | MUST omit |

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

**MySQL syntax:**
```sql
ALTER TABLE table_name ALTER COLUMN column_name SET DEFAULT value;
ALTER TABLE table_name ALTER COLUMN column_name DROP DEFAULT;
```

**DSQL:** MUST use **Table Recreation Pattern**.

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

## ADD/DROP CONSTRAINT Migration

**MySQL syntax:**
```sql
ALTER TABLE table_name ADD CONSTRAINT constraint_name UNIQUE (column_name);
ALTER TABLE table_name ADD CONSTRAINT constraint_name CHECK (condition);
ALTER TABLE table_name DROP CONSTRAINT constraint_name;
-- or MySQL-specific:
ALTER TABLE table_name DROP INDEX index_name;
ALTER TABLE table_name DROP CHECK constraint_name;
```

**DSQL:** MUST use **Table Recreation Pattern**.

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

### Migration Steps (ADD CONSTRAINT)

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

### Migration Steps (DROP CONSTRAINT)

**Step 1: Identify existing constraints**
```sql
readonly_query(
  "SELECT constraint_name, constraint_type
   FROM information_schema.table_constraints
   WHERE table_name = 'target_table'
   AND constraint_type IN ('UNIQUE', 'CHECK')"
)
```

**Step 2: Create new table without the constraint**
```sql
transact([
  "CREATE TABLE target_table_new (
     id UUID PRIMARY KEY,
     email VARCHAR(255),  -- Removed UNIQUE constraint
     other_column TEXT
   )"
])
```

**Step 3: Copy data**
```sql
transact([
  "INSERT INTO target_table_new (id, email, other_column)
   SELECT id, email, other_column
   FROM target_table"
])
```

**Step 4: Verify and swap** (see [Common Pattern](#common-verify--swap-pattern))

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
- Type conversion would fail (e.g., non-numeric VARCHAR to INTEGER)
- Value truncation would occur (e.g., TEXT to VARCHAR(n) exceeding length)
- NOT NULL constraint would be violated
- UNSIGNED check would fail on negative values

```sql
-- Find problematic rows for type conversion
readonly_query(
  "SELECT id, problematic_column FROM target_table
   WHERE problematic_column !~ '^-?[0-9]+$' LIMIT 100"
)

-- Find values exceeding target VARCHAR length
readonly_query(
  "SELECT id, LENGTH(text_column) as len FROM target_table
   WHERE LENGTH(text_column) > 255 LIMIT 100"
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
- **MUST obtain** explicit user approval before proceeding with destructive actions
- **MUST recommend** testing migrations on non-production data first
- **MUST confirm** user has backup or accepts data loss risk

### MySQL-Specific Migration Rules

- **MUST map** all MySQL data types to DSQL equivalents before creating tables
- **MUST convert** AUTO_INCREMENT to UUID with gen_random_uuid(), IDENTITY column with `GENERATED AS IDENTITY (CACHE ...)`, or explicit SEQUENCE — ALWAYS use `GENERATED AS IDENTITY` for auto-incrementing columns (see [AUTO_INCREMENT Migration](#auto_increment-migration))
- **MUST replace** ENUM with VARCHAR and CHECK constraint
- **MUST replace** SET with TEXT (comma-separated)
- **MUST replace** JSON columns with TEXT
- **MUST replace** FOREIGN KEY constraints with application-layer referential integrity
- **MUST replace** ON UPDATE CURRENT_TIMESTAMP with application-layer updates
- **MUST convert** all index creation to use CREATE INDEX ASYNC
- **MUST omit** ENGINE, CHARSET, COLLATE, and other MySQL-specific table options
- **MUST replace** UNSIGNED with CHECK (col >= 0) constraint
- **MUST convert** TINYINT(1) to BOOLEAN

### Technical Requirements

- **MUST validate** data compatibility before type changes
- **MUST batch** tables exceeding 3,000 rows
- **MUST verify** row counts before and after migration
- **MUST recreate** indexes after table swap using ASYNC
- **MUST verify** new table before dropping original table
- **PREFER** cursor-based batching for very large tables
- **PREFER** batches of 500-1,000 rows for optimal throughput
