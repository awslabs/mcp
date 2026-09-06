# MySQL to DSQL: Type Alternatives

Part of [MySQL to DSQL DDL Migration](ddl-operations.md). See
[Common Verify & Swap Pattern](../ddl-migrations/overview.md#common-verify--swap-pattern) for the
shared migration end-pattern.

## Table of Contents

1. [ENUM Type Migration](#enum-type-migration)
2. [SET Type Migration](#set-type-migration)
3. [ON UPDATE CURRENT_TIMESTAMP Migration](#on-update-current_timestamp-migration)
4. [FOREIGN KEY Migration](#foreign-key-migration)

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

DSQL has no array column type. **MUST** serialize the SET into a single-column representation. **WHICH** format is a choice — ASK the user.

```sql
-- PREFER JSONB: filter with `@>`, expand with `jsonb_array_elements_text`,
-- and let the database validate JSON shape on write.
transact([
  "CREATE TABLE user_preferences (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     permissions JSONB  -- '[\"read\",\"write\",\"admin\"]'
   )"
])

-- MAY use TEXT when the column is opaque to the database (application
-- reads the whole value, parses it, never queries inside).
transact([
  "CREATE TABLE user_preferences (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     permissions TEXT  -- e.g. 'read,write,admin'; app validates and parses
   )"
])
```

**Choosing:**

- **PREFER JSONB** when querying inside the value — `permissions @> '[\"admin\"]'`, `jsonb_array_elements_text`, or indexed JSONB paths; values are normalized on write
- **MAY use TEXT** when the column is opaque to the database — application reads the whole value, parses it, never queries inside
- **JSON** is valid when writes dominate (no parse/sort overhead), byte-exact input matters (audit, replay, duplicate keys), or only `->`/`->>` is needed
- When migrating existing JSON columns: **SHOULD** keep them as `JSON`; **MAY** upgrade to `JSONB` if JSONB-only operators or indexed paths are needed

**Note:** Application layer MUST validate `permissions` against the allowed value set on write regardless of the column type. Enum-of-values constraints belong in the application or as a `CHECK` against a derived column.

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

- Before cutover, run an orphan anti-join on the MySQL source and verify every referenced column
  set is backed by `PRIMARY KEY` or `UNIQUE`, not only a non-unique index. A successful DSQL
  `NOT VALID` add proves enforcement for new writes; it does not validate existing rows.
- Preserve the relationship and keep referenced/referencing column types compatible.
- Translate MySQL `ALTER TABLE ... DROP FOREIGN KEY` to
  `ALTER TABLE ... DROP CONSTRAINT`.
- InnoDB creates a referencing-side FK index implicitly. DSQL requires an explicit
  `CREATE INDEX ASYNC` when the access pattern needs that index.
- For post-creation adds, follow
  [Foreign Key Constraints](../foreign-keys.md#dsql-specific-ddl).
- For a tenant-scoped relationship where the database must enforce tenant equality, **MUST**
  include a non-null tenant key on both sides. Preserve ordinary foreign keys for shared or
  globally identified rows.
