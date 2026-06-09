# MySQL to DSQL: Type Alternatives

Part of [MySQL to DSQL DDL Migration](ddl-operations.md). See [Common Verify & Swap Pattern](ddl-operations.md#common-verify--swap-pattern) for the shared migration end-pattern.

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

**DSQL equivalent — pick by access pattern (ASK the user):**

```sql
-- JSONB: queried with @>, ?, or jsonb_array_elements_text; values normalized at write
transact([
  "CREATE TABLE user_preferences (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     permissions JSONB  -- '[\"read\",\"write\",\"admin\"]'
   )"
])

-- JSON: write-heavy or rarely-queried paths; preserves byte-exact input; ->/->> still work
transact([
  "CREATE TABLE user_preferences (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     permissions JSON
   )"
])

-- TEXT: opaque to the database (app-side parse only)
transact([
  "CREATE TABLE user_preferences (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     permissions TEXT  -- e.g. 'read,write,admin'; app validates and parses
   )"
])
```

**Choosing:**

- **JSONB** when the application filters with `permissions @> '[\"admin\"]'`, expands with `jsonb_array_elements_text`, or wants invalid input rejected at write
- **JSON** when writes dominate, when byte-exact input matters (audit, replay), or when only `->`/`->>` is needed
- **TEXT** when the column is opaque to the database — application reads the whole value, parses it, never queries inside

**Note:** Application layer MUST validate `permissions` against the allowed value set on write regardless of the column type — DSQL has no native enum-of-values constraint.

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
